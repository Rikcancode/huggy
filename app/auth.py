from datetime import datetime

from fastapi import Header, HTTPException, Depends, Cookie
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models import User


def get_current_user(
    x_api_key: str | None = Header(None, alias="X-API-Key"),
    mechou_session: str | None = Cookie(None, alias="mechou_session"),
    db: Session = Depends(get_db),
) -> User:
    # 1) Try API key (for OpenClaw, Telegram, CLI)
    if x_api_key:
        user = db.query(User).filter(User.api_key == x_api_key).first()
        if not user:
            raise HTTPException(status_code=401, detail="Invalid API key")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is inactive")
        return user

    # 2) Try cookie-based session (for browser UI)
    if mechou_session:
        try:
            user_id_str, exp_ts_str = mechou_session.split(":", 1)
            exp_ts = int(exp_ts_str)
        except Exception:
            raise HTTPException(status_code=401, detail="Invalid session")
        now_ts = int(datetime.utcnow().timestamp())
        if now_ts > exp_ts:
            raise HTTPException(status_code=401, detail="Session expired")
        user = db.get(User, int(user_id_str))
        if not user:
            raise HTTPException(status_code=401, detail="Invalid session")
        if not user.is_active:
            raise HTTPException(status_code=403, detail="User is inactive")
        return user

    raise HTTPException(status_code=401, detail="Not authenticated")


def require_admin(user: User = Depends(get_current_user)) -> User:
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return user
