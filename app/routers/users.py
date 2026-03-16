import secrets
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import User
from app.routers.auth import hash_password
from app.schemas import UserCreate, UserUpdate, UserOut, UserMeUpdate
from app.auth import require_admin, get_current_user

router = APIRouter(prefix="/api/users", tags=["users"])


@router.get("/me", response_model=UserOut)
def get_current_user_info(user: User = Depends(get_current_user)):
    """Return the authenticated user (for showing name in the UI)."""
    return user


@router.patch("/me", response_model=UserOut)
def update_current_user(data: UserMeUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Update the current user's profile (e.g. avatar)."""
    if data.avatar is not None:
        user.avatar = data.avatar if data.avatar.strip() else None
    db.commit()
    db.refresh(user)
    return user


@router.get("", response_model=list[UserOut])
def list_users(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.query(User).order_by(User.name).all()


@router.post("", response_model=UserOut, status_code=201)
def create_user(data: UserCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = User(
        name=data.name,
        role=data.role,
        language=data.language,
        api_key=secrets.token_urlsafe(32),
    )
    if data.password:
        user.password_hash = hash_password(data.password)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.put("/{user_id}", response_model=UserOut)
def update_user(user_id: int, data: UserUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    payload = data.model_dump(exclude_unset=True)
    password = payload.pop("password", None)
    for k, v in payload.items():
        setattr(user, k, v)
    if password:
        user.password_hash = hash_password(password)
    db.commit()
    db.refresh(user)
    return user


@router.delete("/{user_id}", status_code=204)
def delete_user(user_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
