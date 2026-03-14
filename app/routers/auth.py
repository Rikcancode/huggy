from datetime import datetime, timedelta
import base64
import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from pydantic import BaseModel

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserLogin, UserOut


class ResetAdminPassword(BaseModel):
    setup_token: str
    new_password: str

router = APIRouter(prefix="/auth", tags=["auth"])

SESSION_COOKIE_NAME = "mechou_session"
SESSION_TTL_MINUTES = 7 * 24 * 60  # 7 days


def _pbkdf2(password: str, salt: bytes) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 100_000)


def hash_password(password: str) -> str:
    salt = os.urandom(16)
    dk = _pbkdf2(password, salt)
    return base64.b64encode(salt + dk).decode("ascii")


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    try:
        raw = base64.b64decode(password_hash.encode("ascii"))
    except Exception:
        return False
    if len(raw) < 32:
        return False
    salt, stored = raw[:16], raw[16:]
    candidate = _pbkdf2(password, salt)
    return hmac.compare_digest(candidate, stored)


@router.post("/login", response_model=UserOut)
def login(data: UserLogin, response: Response, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.name == data.name).first()
    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="User is inactive")

    expires = datetime.utcnow() + timedelta(minutes=SESSION_TTL_MINUTES)
    token = f"{user.id}:{int(expires.timestamp())}"
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        secure=False,
        samesite="lax",
        max_age=SESSION_TTL_MINUTES * 60,
        path="/",
    )
    return user


@router.post("/logout")
def logout(response: Response):
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.post("/reset-admin-password")
def reset_admin_password(data: ResetAdminPassword, db: Session = Depends(get_db)):
    """
    One-time reset for the Admin user's password when you're locked out.
    Set GROCERY_SETUP_TOKEN in the environment, then POST with that token and new_password.
    After logging in, unset GROCERY_SETUP_TOKEN for security.
    """
    if not settings.setup_token or not data.setup_token.strip():
        raise HTTPException(status_code=404, detail="Not available")
    if data.setup_token.strip() != settings.setup_token:
        raise HTTPException(status_code=401, detail="Invalid setup token")
    if len(data.new_password.strip()) < 1:
        raise HTTPException(status_code=400, detail="Password cannot be empty")
    admin = db.query(User).filter(User.role == "admin").first()
    if not admin:
        admin = db.query(User).filter(User.name == "Admin").first()
    if not admin:
        raise HTTPException(status_code=404, detail="No admin user found")
    admin.password_hash = hash_password(data.new_password.strip())
    db.commit()
    return {"ok": True, "message": "Password updated for " + admin.name}

