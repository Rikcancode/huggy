"""Kid pickup/drop-off schedule: who's responsible each day."""
from datetime import date
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import KidScheduleEntry, User
from app.auth import get_current_user

router = APIRouter(prefix="/api/kid-schedule", tags=["kid-schedule"])


class KidSlotUpdate(BaseModel):
    assigned_user_id: int | None = None
    notes: str | None = None


class KidSlotOut(BaseModel):
    id: int
    year: int
    week: int
    day: int
    slot: str
    assigned_user_id: int | None = None
    assigned_user_name: str | None = None
    assigned_user_avatar: str | None = None
    notes: str | None = None
    model_config = {"from_attributes": True}


@router.get("", response_model=list[KidSlotOut])
def get_week(
    year: int | None = Query(None),
    week: int | None = Query(None, ge=1, le=53),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    y, w = year or today.isocalendar()[0], week or today.isocalendar()[1]
    entries = (
        db.query(KidScheduleEntry)
        .filter(KidScheduleEntry.year == y, KidScheduleEntry.week == w)
        .all()
    )
    by_key = {(e.day, e.slot): e for e in entries}
    out = []
    for day in range(1, 8):
        for slot in ["morning", "afternoon"]:
            if (day, slot) in by_key:
                e = by_key[(day, slot)]
            else:
                e = KidScheduleEntry(year=y, week=w, day=day, slot=slot)
                db.add(e)
                db.commit()
                db.refresh(e)
            out.append(KidSlotOut(
                id=e.id,
                year=e.year,
                week=e.week,
                day=e.day,
                slot=e.slot,
                assigned_user_id=e.assigned_user_id,
                assigned_user_name=e.assigned_user.name if e.assigned_user else None,
                assigned_user_avatar=e.assigned_user.avatar if e.assigned_user else None,
                notes=e.notes,
            ))
    return out


@router.put("/slot", response_model=KidSlotOut)
def set_slot(
    year: int = Query(...),
    week: int = Query(..., ge=1, le=53),
    day: int = Query(..., ge=1, le=7),
    slot: str = Query(..., pattern="^(morning|afternoon)$"),
    data: KidSlotUpdate = ...,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(KidScheduleEntry)
        .filter(KidScheduleEntry.year == year, KidScheduleEntry.week == week,
                KidScheduleEntry.day == day, KidScheduleEntry.slot == slot)
        .first()
    )
    if not row:
        row = KidScheduleEntry(year=year, week=week, day=day, slot=slot)
        db.add(row)
    row.assigned_user_id = data.assigned_user_id
    row.notes = data.notes
    db.commit()
    db.refresh(row)
    assigned = db.get(User, row.assigned_user_id) if row.assigned_user_id else None
    return KidSlotOut(
        id=row.id, year=row.year, week=row.week, day=row.day, slot=row.slot,
        assigned_user_id=row.assigned_user_id,
        assigned_user_name=assigned.name if assigned else None,
        assigned_user_avatar=assigned.avatar if assigned else None,
        notes=row.notes,
    )
