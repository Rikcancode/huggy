from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Response
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User
from app.schemas import UserLogin, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

SESSION_COOKIE_NAME = "mechou_session"
SESSION_TTL_MINUTES = 7 * 24 * 60  # 7 days


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if not password_hash:
        return False
    return pwd_context.verify(password, password_hash)


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

