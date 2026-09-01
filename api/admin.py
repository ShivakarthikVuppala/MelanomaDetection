"""
Admin API
=========

Secure administrative endpoints for managing users and settings.
Requires the 'admin' role.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field

from .auth import (
    get_admin_user, 
    _get_conn, 
    UserOut, 
    _verify_password, 
    _hash_password
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


@router.get("/users", response_model=List[UserOut])
def get_all_users(admin: dict = Depends(get_admin_user)):
    """Fetch all registered users. Admin only."""
    conn = _get_conn()
    rows = conn.execute("SELECT * FROM users ORDER BY created_at DESC").fetchall()
    conn.close()

    return [
        UserOut(
            id=row["id"],
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row["phone"],
            email=row["email"],
            created_at=row["created_at"],
            role=row["role"]
        )
        for row in rows
    ]


@router.delete("/users/{user_id}")
def delete_user(user_id: int, admin: dict = Depends(get_admin_user)):
    """Delete a normal user. Admin only."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    conn = _get_conn()
    
    # Ensure the user exists and isn't another admin
    target_user = conn.execute("SELECT role FROM users WHERE id = ?", (user_id,)).fetchone()
    if not target_user:
        conn.close()
        raise HTTPException(status_code=404, detail="User not found.")
    
    if target_user["role"] == "admin":
        conn.close()
        raise HTTPException(status_code=403, detail="Cannot delete another administrator.")

    conn.execute("DELETE FROM users WHERE id = ?", (user_id,))
    conn.commit()
    conn.close()

    return {"message": "User deleted successfully."}


@router.put("/password")
def change_admin_password(body: ChangePasswordRequest, admin: dict = Depends(get_admin_user)):
    """Change the admin's password."""
    conn = _get_conn()
    row = conn.execute("SELECT password_hash FROM users WHERE id = ?", (admin["id"],)).fetchone()
    
    if not _verify_password(body.current_password, row["password_hash"]):
        conn.close()
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
        
    new_hash = _hash_password(body.new_password)
    conn.execute("UPDATE users SET password_hash = ? WHERE id = ?", (new_hash, admin["id"]))
    conn.commit()
    conn.close()

    return {"message": "Password changed successfully."}
