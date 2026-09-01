"""
Authentication API
===================

User registration, login, and profile management with MongoDB + bcrypt + JWT.
"""

import os
import re
import secrets
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field
from bson.objectid import ObjectId

from .db import get_db

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
AUTH_SECRET_KEY = os.getenv("AUTH_SECRET_KEY", secrets.token_hex(32))
JWT_ALGORITHM = "HS256"
JWT_EXPIRY_HOURS = 24

# ---------------------------------------------------------------------------
# Lazy imports — keep startup fast if auth deps are missing
# ---------------------------------------------------------------------------
_bcrypt = None
_jose = None


def _get_bcrypt():
    global _bcrypt
    if _bcrypt is None:
        import bcrypt
        _bcrypt = bcrypt
    return _bcrypt


def _get_jose():
    global _jose
    if _jose is None:
        import jose  # noqa: F811 — delayed import
        _jose = jose
    return _jose


def _hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    b = _get_bcrypt()
    return b.hashpw(password.encode("utf-8"), b.gensalt()).decode("utf-8")


def _verify_password(password: str, hashed: str) -> bool:
    """Verify a password against a bcrypt hash."""
    b = _get_bcrypt()
    return b.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))


# ---------------------------------------------------------------------------
# Database initialization
# ---------------------------------------------------------------------------
async def seed_admin():
    """Seed the Admin User in MongoDB on startup."""
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_pass = os.getenv("ADMIN_INITIAL_PASSWORD")
    if not admin_email or not admin_pass:
        return

    db = get_db()
    if db is None:
        return

    existing_admin = await db["users"].find_one({"email": admin_email})
    if not existing_admin:
        now = datetime.now(timezone.utc).isoformat()
        p_hash = _hash_password(admin_pass)
        await db["users"].insert_one({
            "first_name": "System",
            "last_name": "Administrator",
            "phone": "",
            "email": admin_email,
            "password_hash": p_hash,
            "created_at": now,
            "role": "admin"
        })
        logger.info(f"Initialized Admin user with email: {admin_email}")
    else:
        # Ensure it has admin role
        if existing_admin.get("role") != "admin":
            await db["users"].update_one(
                {"email": admin_email},
                {"$set": {"role": "admin"}}
            )


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    phone: str = Field(..., min_length=1, max_length=30)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class LoginRequest(BaseModel):
    email: str
    password: str


class VerifyEmailRequest(BaseModel):
    email: str
    otp: str


class ResendOtpRequest(BaseModel):
    email: str


class ProfileUpdateRequest(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    phone: Optional[str] = None
    email: Optional[str] = None


class UserOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    phone: str
    email: str
    created_at: str
    role: str


class AuthResponse(BaseModel):
    token: str
    user: UserOut


# ---------------------------------------------------------------------------
# Token helpers
# ---------------------------------------------------------------------------

def _create_token(user_id: str, email: str) -> str:
    jose = _get_jose()
    from jose import jwt as jose_jwt
    payload = {
        "sub": str(user_id),
        "email": email,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRY_HOURS),
        "iat": datetime.now(timezone.utc),
    }
    return jose_jwt.encode(payload, AUTH_SECRET_KEY, algorithm=JWT_ALGORITHM)


def _decode_token(token: str) -> dict:
    from jose import jwt as jose_jwt, JWTError
    try:
        return jose_jwt.decode(token, AUTH_SECRET_KEY, algorithms=[JWT_ALGORITHM])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token.")


# ---------------------------------------------------------------------------
# Auth dependency
# ---------------------------------------------------------------------------

async def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and validate the current user from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    token = authorization[7:]
    payload = _decode_token(token)
    user_id = payload["sub"]

    db = get_db()
    if db is None:
        raise HTTPException(status_code=500, detail="Database unavailable.")

    try:
        obj_id = ObjectId(user_id)
    except Exception:
        raise HTTPException(status_code=401, detail="Invalid user ID format.")

    user = await db["users"].find_one({"_id": obj_id})
    if user is None:
        raise HTTPException(status_code=401, detail="User not found.")

    user["id"] = str(user["_id"])
    return user


async def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
    """Ensure the current user has the admin role."""
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Forbidden: Admin access required.")
    return current_user


# ---------------------------------------------------------------------------
# Validation helpers
# ---------------------------------------------------------------------------
EMAIL_RE = re.compile(r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$")
PHONE_RE = re.compile(r"^[+]?[\d\s\-().]{7,20}$")


def _validate_email(email: str) -> str:
    email = email.strip().lower()
    if not EMAIL_RE.match(email):
        raise HTTPException(status_code=422, detail="Please enter a valid email address.")
    return email


def _validate_phone(phone: str) -> str:
    phone = phone.strip()
    if not PHONE_RE.match(phone):
        raise HTTPException(status_code=422, detail="Please enter a valid phone number.")
    return phone


# ---------------------------------------------------------------------------
# Helpers for OTP and Email
# ---------------------------------------------------------------------------

def _generate_otp() -> str:
    return str(secrets.randbelow(1000000)).zfill(6)


def _send_otp_email(email: str, first_name: str, otp: str):
    email_host = os.getenv("EMAIL_HOST")
    if not email_host:
        logger.warning(f"No EMAIL_HOST configured. OTP for {email} is: {otp}")
        return
        
    try:
        msg = EmailMessage()
        msg.set_content(f"Hello {first_name},\n\nYour verification code is:\n\n{otp}\n\nThis code expires in 10 minutes.\n\nMelanoma Detection Team")
        msg['Subject'] = "Verify your Melanoma Detection account"
        msg['From'] = os.getenv("EMAIL_USER", "noreply@meladetect.local")
        msg['To'] = email
        
        server = smtplib.SMTP(email_host, int(os.getenv("EMAIL_PORT", 587)))
        server.starttls()
        server.login(os.getenv("EMAIL_USER"), os.getenv("EMAIL_PASSWORD"))
        server.send_message(msg)
        server.quit()
    except Exception as e:
        logger.error(f"Failed to send email to {email}: {e}")


async def _check_rate_limit(db, action: str, identifier: str, limit: int, window_minutes: int) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    await db["rate_limits"].delete_many({"timestamp": {"$lt": cutoff}})
    
    count = await db["rate_limits"].count_documents({
        "action": action, 
        "identifier": identifier, 
        "timestamp": {"$gte": cutoff}
    })
    
    if count >= limit:
        return False
        
    await db["rate_limits"].insert_one({
        "action": action,
        "identifier": identifier,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    return True


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/auth")


@router.post("/signup")
async def signup(body: SignupRequest):
    """Register a new user account (creates pending registration)."""
    email = _validate_email(body.email)
    phone = _validate_phone(body.phone)

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        if not await _check_rate_limit(db, "signup", email, 5, 60):
            raise HTTPException(status_code=429, detail="Too many signup requests. Please try again later.")

        # Check for duplicate email in users
        existing = await db["users"].find_one({"email": email})
        if existing:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists.",
            )
            
        password_hash = _hash_password(body.password)
        otp = _generate_otp()
        otp_hash = _hash_password(otp)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        await db["pending_registrations"].update_one(
            {"email": email},
            {"$set": {
                "first_name": body.first_name.strip(),
                "last_name": body.last_name.strip(),
                "phone": phone,
                "password_hash": password_hash,
                "otp_hash": otp_hash,
                "expires_at": expires_at,
                "attempts": 0
            }},
            upsert=True
        )
        
        import threading
        threading.Thread(target=_send_otp_email, args=(email, body.first_name.strip(), otp)).start()
        
    except HTTPException:
        raise
    except Exception:
        logger.exception("Signup DB error")
        raise HTTPException(status_code=500, detail="Account creation failed. Please try again.")

    return {"message": "OTP sent to email.", "email": email}


@router.post("/verify-email")
async def verify_email(body: VerifyEmailRequest):
    """Validate OTP and create user."""
    email = body.email.strip().lower()
    
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        if not await _check_rate_limit(db, "verify_otp", email, 5, 10):
            raise HTTPException(status_code=429, detail="Too many verification attempts.")
            
        pending = await db["pending_registrations"].find_one({"email": email})
        if not pending:
            raise HTTPException(status_code=400, detail="No pending registration found for this email.")
            
        if datetime.fromisoformat(pending["expires_at"]) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="This verification code has expired.")
            
        if pending.get("attempts", 0) >= 5:
            await db["pending_registrations"].delete_one({"email": email})
            raise HTTPException(status_code=400, detail="Too many failed attempts. Please sign up again.")
            
        if not _verify_password(body.otp, pending["otp_hash"]):
            await db["pending_registrations"].update_one(
                {"email": email},
                {"$inc": {"attempts": 1}}
            )
            raise HTTPException(status_code=400, detail="Invalid verification code.")
            
        now = datetime.now(timezone.utc).isoformat()
        result = await db["users"].insert_one({
            "first_name": pending["first_name"],
            "last_name": pending["last_name"],
            "phone": pending["phone"],
            "email": email,
            "password_hash": pending["password_hash"],
            "created_at": now,
            "role": "user"
        })
        await db["pending_registrations"].delete_one({"email": email})
        
    except HTTPException:
        raise
        
    return {"message": "Email verified and account created."}


@router.post("/resend-otp")
async def resend_otp(body: ResendOtpRequest):
    """Resend a new OTP to a pending registration."""
    email = body.email.strip().lower()
    
    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    try:
        if not await _check_rate_limit(db, "send_otp", email, 3, 15):
            raise HTTPException(status_code=429, detail="Too many verification requests. Please try again later.")
            
        pending = await db["pending_registrations"].find_one({"email": email})
        if not pending:
            raise HTTPException(status_code=400, detail="No pending registration found.")
            
        otp = _generate_otp()
        otp_hash = _hash_password(otp)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        await db["pending_registrations"].update_one(
            {"email": email},
            {"$set": {
                "otp_hash": otp_hash,
                "expires_at": expires_at,
                "attempts": 0
            }}
        )
        
        import threading
        threading.Thread(target=_send_otp_email, args=(email, pending["first_name"], otp)).start()
        
    except HTTPException:
        raise
        
    return {"message": "A new verification code has been sent."}


@router.post("/login", response_model=AuthResponse)
async def login(body: LoginRequest):
    """Authenticate and return a JWT token."""
    email = body.email.strip().lower()

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    user = await db["users"].find_one({"email": email})
    
    if user is None or not _verify_password(body.password, user["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user_id_str = str(user["_id"])
    token = _create_token(user_id_str, user["email"])

    return AuthResponse(
        token=token,
        user=UserOut(
            id=user_id_str,
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone=user["phone"],
            email=user["email"],
            created_at=user["created_at"],
            role=user.get("role", "user"),
        ),
    )


@router.get("/me", response_model=UserOut)
async def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserOut(
        id=current_user["id"],
        first_name=current_user["first_name"],
        last_name=current_user["last_name"],
        phone=current_user["phone"],
        email=current_user["email"],
        created_at=current_user["created_at"],
        role=current_user.get("role", "user"),
    )


@router.put("/me", response_model=UserOut)
async def update_me(body: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
    """Update the authenticated user's profile."""
    updates = {}
    if body.first_name is not None:
        val = body.first_name.strip()
        if not val:
            raise HTTPException(status_code=422, detail="First name cannot be empty.")
        updates["first_name"] = val

    if body.last_name is not None:
        val = body.last_name.strip()
        if not val:
            raise HTTPException(status_code=422, detail="Last name cannot be empty.")
        updates["last_name"] = val

    if body.phone is not None:
        updates["phone"] = _validate_phone(body.phone)

    db = get_db()
    if db is None:
        raise HTTPException(status_code=503, detail="Database unavailable.")

    if body.email is not None:
        new_email = _validate_email(body.email)
        if new_email != current_user["email"]:
            existing = await db["users"].find_one({
                "email": new_email,
                "_id": {"$ne": ObjectId(current_user["id"])}
            })
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="This email is already in use by another account.",
                )
        updates["email"] = new_email

    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")

    await db["users"].update_one(
        {"_id": ObjectId(current_user["id"])},
        {"$set": updates}
    )

    row = await db["users"].find_one({"_id": ObjectId(current_user["id"])})

    return UserOut(
        id=str(row["_id"]),
        first_name=row["first_name"],
        last_name=row["last_name"],
        phone=row["phone"],
        email=row["email"],
        created_at=row["created_at"],
        role=row.get("role", "user"),
    )
