"""
Authentication API
===================

User registration, login, and profile management with SQLite + bcrypt + JWT.
"""

import os
import re
import sqlite3
import secrets
import logging
import smtplib
from email.message import EmailMessage
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Header
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "data" / "users.db"
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
# Database helpers
# ---------------------------------------------------------------------------
def _ensure_db():
    """Create the users table if it doesn't exist."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            first_name  TEXT    NOT NULL,
            last_name   TEXT    NOT NULL,
            phone       TEXT    NOT NULL,
            email       TEXT    NOT NULL UNIQUE,
            password_hash TEXT  NOT NULL,
            created_at  TEXT    NOT NULL,
            role        TEXT    NOT NULL DEFAULT 'user'
        )
    """)
    # Migration: Add role column if it doesn't exist
    try:
        conn.execute("ALTER TABLE users ADD COLUMN role TEXT NOT NULL DEFAULT 'user'")
    except sqlite3.OperationalError:
        pass  # Column already exists
        
    conn.execute("""
        CREATE TABLE IF NOT EXISTS pending_registrations (
            email         TEXT    PRIMARY KEY,
            first_name    TEXT    NOT NULL,
            last_name     TEXT    NOT NULL,
            phone         TEXT    NOT NULL,
            password_hash TEXT    NOT NULL,
            otp_hash      TEXT    NOT NULL,
            expires_at    TEXT    NOT NULL,
            attempts      INTEGER DEFAULT 0
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS rate_limits (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            action      TEXT    NOT NULL,
            identifier  TEXT    NOT NULL,
            timestamp   TEXT    NOT NULL
        )
    """)
    conn.commit()

    # Seed Admin User
    admin_email = os.getenv("ADMIN_EMAIL")
    admin_pass = os.getenv("ADMIN_INITIAL_PASSWORD")
    if admin_email and admin_pass:
        existing_admin = conn.execute("SELECT id FROM users WHERE email = ?", (admin_email,)).fetchone()
        if not existing_admin:
            now = datetime.now(timezone.utc).isoformat()
            p_hash = _hash_password(admin_pass)
            conn.execute(
                """INSERT INTO users (first_name, last_name, phone, email, password_hash, created_at, role)
                   VALUES (?, ?, ?, ?, ?, ?, ?)""",
                ("System", "Administrator", "", admin_email, p_hash, now, "admin"),
            )
            logger.info(f"Initialized Admin user with email: {admin_email}")
        else:
            # Ensure it has admin role
            conn.execute("UPDATE users SET role = 'admin' WHERE email = ?", (admin_email,))
            
    conn.commit()
    conn.close()


def _get_conn() -> sqlite3.Connection:
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    return conn


# Ensure DB on module import
_ensure_db()

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
    id: int
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

def _create_token(user_id: int, email: str) -> str:
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

def get_current_user(authorization: str = Header(...)) -> dict:
    """Extract and validate the current user from the Authorization header."""
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid authorization header.")
    token = authorization[7:]
    payload = _decode_token(token)
    user_id = int(payload["sub"])

    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()
    conn.close()

    if row is None:
        raise HTTPException(status_code=401, detail="User not found.")

    return dict(row)


def get_admin_user(current_user: dict = Depends(get_current_user)) -> dict:
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


def _check_rate_limit(conn, action: str, identifier: str, limit: int, window_minutes: int) -> bool:
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=window_minutes)).isoformat()
    conn.execute("DELETE FROM rate_limits WHERE timestamp < ?", (cutoff,))
    
    count = conn.execute(
        "SELECT COUNT(*) FROM rate_limits WHERE action = ? AND identifier = ? AND timestamp >= ?",
        (action, identifier, cutoff)
    ).fetchone()[0]
    
    if count >= limit:
        return False
        
    conn.execute(
        "INSERT INTO rate_limits (action, identifier, timestamp) VALUES (?, ?, ?)",
        (action, identifier, datetime.now(timezone.utc).isoformat())
    )
    return True


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------
router = APIRouter(prefix="/api/auth")


@router.post("/signup")
def signup(body: SignupRequest):
    """Register a new user account (creates pending registration)."""
    email = _validate_email(body.email)
    phone = _validate_phone(body.phone)

    conn = _get_conn()
    try:
        if not _check_rate_limit(conn, "signup", email, 5, 60):
            raise HTTPException(status_code=429, detail="Too many signup requests. Please try again later.")

        # Check for duplicate email in users
        existing = conn.execute("SELECT id FROM users WHERE email = ?", (email,)).fetchone()
        if existing:
            raise HTTPException(
                status_code=409,
                detail="An account with this email already exists.",
            )
            
        password_hash = _hash_password(body.password)
        otp = _generate_otp()
        otp_hash = _hash_password(otp)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        conn.execute("""
            INSERT INTO pending_registrations (email, first_name, last_name, phone, password_hash, otp_hash, expires_at, attempts)
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ON CONFLICT(email) DO UPDATE SET
                first_name=excluded.first_name,
                last_name=excluded.last_name,
                phone=excluded.phone,
                password_hash=excluded.password_hash,
                otp_hash=excluded.otp_hash,
                expires_at=excluded.expires_at,
                attempts=0
        """, (email, body.first_name.strip(), body.last_name.strip(), phone, password_hash, otp_hash, expires_at))
        
        conn.commit()
        
        import threading
        threading.Thread(target=_send_otp_email, args=(email, body.first_name.strip(), otp)).start()
        
    except HTTPException:
        raise
    except Exception:
        logger.exception("Signup DB error")
        raise HTTPException(status_code=500, detail="Account creation failed. Please try again.")
    finally:
        conn.close()

    return {"message": "OTP sent to email.", "email": email}


@router.post("/verify-email")
def verify_email(body: VerifyEmailRequest):
    """Validate OTP and create user."""
    email = body.email.strip().lower()
    
    conn = _get_conn()
    try:
        if not _check_rate_limit(conn, "verify_otp", email, 5, 10):
            raise HTTPException(status_code=429, detail="Too many verification attempts.")
            
        pending = conn.execute("SELECT * FROM pending_registrations WHERE email = ?", (email,)).fetchone()
        if not pending:
            raise HTTPException(status_code=400, detail="No pending registration found for this email.")
            
        if datetime.fromisoformat(pending["expires_at"]) < datetime.now(timezone.utc):
            raise HTTPException(status_code=400, detail="This verification code has expired.")
            
        if pending["attempts"] >= 5:
            conn.execute("DELETE FROM pending_registrations WHERE email = ?", (email,))
            conn.commit()
            raise HTTPException(status_code=400, detail="Too many failed attempts. Please sign up again.")
            
        if not _verify_password(body.otp, pending["otp_hash"]):
            conn.execute("UPDATE pending_registrations SET attempts = attempts + 1 WHERE email = ?", (email,))
            conn.commit()
            raise HTTPException(status_code=400, detail="Invalid verification code.")
            
        now = datetime.now(timezone.utc).isoformat()
        cursor = conn.execute(
            """INSERT INTO users (first_name, last_name, phone, email, password_hash, created_at, role)
               VALUES (?, ?, ?, ?, ?, ?, 'user')""",
            (pending["first_name"], pending["last_name"], pending["phone"], email, pending["password_hash"], now),
        )
        conn.execute("DELETE FROM pending_registrations WHERE email = ?", (email,))
        conn.commit()
        
        user_id = cursor.lastrowid
        
    except HTTPException:
        raise
    finally:
        conn.close()
        
    return {"message": "Email verified and account created."}


@router.post("/resend-otp")
def resend_otp(body: ResendOtpRequest):
    """Resend a new OTP to a pending registration."""
    email = body.email.strip().lower()
    
    conn = _get_conn()
    try:
        if not _check_rate_limit(conn, "send_otp", email, 3, 15):
            raise HTTPException(status_code=429, detail="Too many verification requests. Please try again later.")
            
        pending = conn.execute("SELECT first_name FROM pending_registrations WHERE email = ?", (email,)).fetchone()
        if not pending:
            raise HTTPException(status_code=400, detail="No pending registration found.")
            
        otp = _generate_otp()
        otp_hash = _hash_password(otp)
        expires_at = (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()
        
        conn.execute(
            "UPDATE pending_registrations SET otp_hash = ?, expires_at = ?, attempts = 0 WHERE email = ?",
            (otp_hash, expires_at, email)
        )
        conn.commit()
        
        import threading
        threading.Thread(target=_send_otp_email, args=(email, pending["first_name"], otp)).start()
        
    except HTTPException:
        raise
    finally:
        conn.close()
        
    return {"message": "A new verification code has been sent."}


@router.post("/login", response_model=AuthResponse)
def login(body: LoginRequest):
    """Authenticate and return a JWT token."""
    email = body.email.strip().lower()

    conn = _get_conn()
    row = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
    conn.close()

    if row is None or not _verify_password(body.password, row["password_hash"]):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    user = dict(row)
    token = _create_token(user["id"], user["email"])

    return AuthResponse(
        token=token,
        user=UserOut(
            id=user["id"],
            first_name=user["first_name"],
            last_name=user["last_name"],
            phone=user["phone"],
            email=user["email"],
            created_at=user["created_at"],
            role=user["role"],
        ),
    )


@router.get("/me", response_model=UserOut)
def get_me(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's profile."""
    return UserOut(
        id=current_user["id"],
        first_name=current_user["first_name"],
        last_name=current_user["last_name"],
        phone=current_user["phone"],
        email=current_user["email"],
        created_at=current_user["created_at"],
        role=current_user["role"],
    )


@router.put("/me", response_model=UserOut)
def update_me(body: ProfileUpdateRequest, current_user: dict = Depends(get_current_user)):
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

    if body.email is not None:
        new_email = _validate_email(body.email)
        if new_email != current_user["email"]:
            conn = _get_conn()
            existing = conn.execute(
                "SELECT id FROM users WHERE email = ? AND id != ?",
                (new_email, current_user["id"]),
            ).fetchone()
            conn.close()
            if existing:
                raise HTTPException(
                    status_code=409,
                    detail="This email is already in use by another account.",
                )
        updates["email"] = new_email

    if not updates:
        raise HTTPException(status_code=422, detail="No fields to update.")

    set_clause = ", ".join(f"{k} = ?" for k in updates)
    values = list(updates.values()) + [current_user["id"]]

    conn = _get_conn()
    conn.execute(f"UPDATE users SET {set_clause} WHERE id = ?", values)
    conn.commit()

    row = conn.execute("SELECT * FROM users WHERE id = ?", (current_user["id"],)).fetchone()
    conn.close()

    return UserOut(
        id=row["id"],
        first_name=row["first_name"],
        last_name=row["last_name"],
        phone=row["phone"],
        email=row["email"],
        created_at=row["created_at"],
        role=row["role"],
    )
