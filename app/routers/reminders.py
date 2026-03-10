from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import RepurchaseReminder, User
from app.schemas import ReminderCreate, ReminderUpdate, ReminderOut
from app.auth import get_current_user, require_admin

router = APIRouter(prefix="/api/reminders", tags=["reminders"])


@router.get("", response_model=list[ReminderOut])
def list_reminders(db: Session = Depends(get_db)):
    return (
        db.query(RepurchaseReminder)
        .options(joinedload(RepurchaseReminder.library_item))
        .order_by(RepurchaseReminder.next_due)
        .all()
    )


@router.get("/due", response_model=list[ReminderOut])
def get_due_reminders(db: Session = Depends(get_db)):
    now = datetime.utcnow()
    return (
        db.query(RepurchaseReminder)
        .options(joinedload(RepurchaseReminder.library_item))
        .filter(RepurchaseReminder.active.is_(True))
        .filter(
            (RepurchaseReminder.next_due <= now) | (RepurchaseReminder.next_due.is_(None))
        )
        .all()
    )


@router.post("", response_model=ReminderOut, status_code=201)
def create_reminder(data: ReminderCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    r = RepurchaseReminder(
        library_item_id=data.library_item_id,
        interval_days=data.interval_days,
        active=data.active,
        next_due=datetime.utcnow() + timedelta(days=data.interval_days),
    )
    db.add(r)
    db.commit()
    db.refresh(r)
    return r


@router.put("/{reminder_id}", response_model=ReminderOut)
def update_reminder(reminder_id: int, data: ReminderUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    r = db.get(RepurchaseReminder, reminder_id)
    if not r:
        raise HTTPException(404, "Reminder not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(r, k, v)
    db.commit()
    db.refresh(r)
    return r


@router.delete("/{reminder_id}", status_code=204)
def delete_reminder(reminder_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    r = db.get(RepurchaseReminder, reminder_id)
    if not r:
        raise HTTPException(404, "Reminder not found")
    db.delete(r)
    db.commit()
