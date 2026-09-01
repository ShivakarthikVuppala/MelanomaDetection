"""
Admin API
=========

Secure administrative endpoints for managing users and settings.
Requires the 'admin' role.
"""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson.objectid import ObjectId

from .db import get_db
from .auth import (
    get_admin_user, 
    UserOut, 
    _verify_password, 
    _hash_password
)

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=6, max_length=128)


@router.get("/users", response_model=List[UserOut])
async def get_all_users(admin: dict = Depends(get_admin_user)):
    """Fetch all registered users. Admin only."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    cursor = db["users"].find({}).sort("created_at", -1)
    users = []
    async for row in cursor:
        users.append(
            UserOut(
                id=str(row["_id"]),
                first_name=row["first_name"],
                last_name=row["last_name"],
                phone=row["phone"],
                email=row["email"],
                created_at=row["created_at"],
                role=row.get("role", "user")
            )
        )
    return users


@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a normal user. Admin only."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")
    
    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    # Ensure the user exists and isn't another admin
    target_user = await db["users"].find_one({"_id": obj_id})
    if not target_user:
        raise HTTPException(status_code=404, detail="User not found.")
    
    if target_user.get("role") == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete another administrator.")

    await db["users"].delete_one({"_id": obj_id})

    return {"message": "User deleted successfully."}


@router.put("/password")
async def change_admin_password(body: ChangePasswordRequest, admin: dict = Depends(get_admin_user)):
    """Change the admin's password."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        obj_id = ObjectId(admin["id"])
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID format.")

    row = await db["users"].find_one({"_id": obj_id})
    if not row:
        raise HTTPException(status_code=404, detail="Admin user not found.")
    
    if not _verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")
        
    new_hash = _hash_password(body.new_password)
    await db["users"].update_one(
        {"_id": obj_id},
        {"$set": {"password_hash": new_hash}}
    )

    return {"message": "Password changed successfully."}
