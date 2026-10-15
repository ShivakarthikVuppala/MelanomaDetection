"""
Admin API
=========

Secure administrative endpoints — all data served from MongoDB.
Requires the 'admin' role.
"""

from typing import List
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from bson.objectid import ObjectId

from .db import get_db
from .auth import get_admin_user, UserOut, _verify_password, _hash_password, SELF_SIGNUP_ROLES

router = APIRouter(prefix="/api/admin", tags=["admin"])


class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password:     str = Field(..., min_length=6, max_length=128)


class RoleUpdateRequest(BaseModel):
    role: str = Field(..., max_length=30)


# ---------------------------------------------------------------------------
# GET /api/admin/users  — list all users
# ---------------------------------------------------------------------------
@router.get("/users", response_model=List[UserOut])
async def get_all_users(admin: dict = Depends(get_admin_user)):
    """Return all registered users, newest first. Admin only."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    users = []
    async for row in db["users"].find({}).sort("created_at", -1):
        users.append(UserOut(
            id=str(row["_id"]),
            first_name=row["first_name"],
            last_name=row["last_name"],
            phone=row.get("phone", ""),
            email=row["email"],
            created_at=row["created_at"],
            role=row.get("role", "user"),
        ))
    return users


# ---------------------------------------------------------------------------
# DELETE /api/admin/users/{user_id}  — remove a user
# ---------------------------------------------------------------------------
@router.delete("/users/{user_id}")
async def delete_user(user_id: str, admin: dict = Depends(get_admin_user)):
    """Delete a normal user by MongoDB ObjectId string. Admin only."""
    if user_id == admin["id"]:
        raise HTTPException(status_code=400, detail="Cannot delete your own admin account.")

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID.")

    target = await db["users"].find_one({"_id": obj_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.get("role") == "admin":
        raise HTTPException(status_code=403, detail="Cannot delete another administrator.")

    await db["users"].delete_one({"_id": obj_id})
    return {"message": "User deleted successfully."}


# ---------------------------------------------------------------------------
# PUT /api/admin/users/{user_id}/role  — change a user's role
# ---------------------------------------------------------------------------
@router.put("/users/{user_id}/role", response_model=UserOut)
async def set_user_role(
    user_id: str,
    body: RoleUpdateRequest,
    admin: dict = Depends(get_admin_user),
):
    """Change a user's role. Admin only.

    Assignable roles are limited to user/practitioner/researcher. Administrators
    are not created or demoted here, mirroring the delete-user safeguard.
    """
    role = (body.role or "").strip().lower()
    if role not in SELF_SIGNUP_ROLES:
        raise HTTPException(status_code=422, detail="Invalid role. Choose user, practitioner, or researcher.")

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid user ID.")

    target = await db["users"].find_one({"_id": obj_id})
    if not target:
        raise HTTPException(status_code=404, detail="User not found.")
    if target.get("role") == "admin":
        raise HTTPException(status_code=403, detail="Cannot change an administrator's role.")

    await db["users"].update_one({"_id": obj_id}, {"$set": {"role": role}})
    row = await db["users"].find_one({"_id": obj_id})
    return UserOut(
        id=str(row["_id"]),
        first_name=row["first_name"],
        last_name=row["last_name"],
        phone=row.get("phone", ""),
        email=row["email"],
        created_at=row["created_at"],
        role=row.get("role", "user"),
        is_test_account=bool(row.get("is_test_account", False)),
    )


# ---------------------------------------------------------------------------
# PUT /api/admin/password  — change admin password
# ---------------------------------------------------------------------------
@router.put("/password")
async def change_admin_password(
    body: ChangePasswordRequest,
    admin: dict = Depends(get_admin_user),
):
    """Change the admin's own password."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    row = await db["users"].find_one({"_id": ObjectId(admin["id"])})
    if not row:
        raise HTTPException(status_code=404, detail="Admin user not found.")

    if not _verify_password(body.current_password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Current password is incorrect.")

    new_hash = _hash_password(body.new_password)
    await db["users"].update_one(
        {"_id": ObjectId(admin["id"])},
        {"$set": {"password_hash": new_hash}},
    )
    return {"message": "Password changed successfully."}


# ---------------------------------------------------------------------------
# GET /api/admin/stats  — dashboard numbers
# ---------------------------------------------------------------------------
@router.get("/stats")
async def get_admin_stats(admin: dict = Depends(get_admin_user)):
    """Return user count stats for the admin dashboard."""
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    total    = await db["users"].count_documents({})
    cutoff   = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat()
    new_30d  = await db["users"].count_documents({"created_at": {"$gte": cutoff}})
    analyses = await db["analyses"].count_documents({})

    return {
        "total_users":     total,
        "new_users_30d":   new_30d,
        "total_analyses":  analyses,
    }
