from datetime import datetime, timedelta
import base64
import hashlib
import hmac
import os

from fastapi import APIRouter, Depends, HTTPException, Response
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserLogin, UserOut

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

