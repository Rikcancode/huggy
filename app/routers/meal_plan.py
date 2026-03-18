from datetime import date
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import MealPlanEntry
from app.schemas import MealPlanEntryOut, MealPlanDayUpdate
from app.auth import get_current_user

router = APIRouter(prefix="/api/meal-plan", tags=["meal-plan"])


def _iso_week(d: date):
    """Return (iso_year, iso_week) for date."""
    iso = d.isocalendar()
    return iso[0], iso[1]


@router.get("", response_model=list[MealPlanEntryOut])
def get_week(
    year: int | None = Query(None, description="ISO year"),
    week: int | None = Query(None, ge=1, le=53, description="ISO week"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    today = date.today()
    y, w = year or today.isocalendar()[0], week or today.isocalendar()[1]
    entries = (
        db.query(MealPlanEntry)
        .filter(MealPlanEntry.year == y, MealPlanEntry.week == w)
        .order_by(MealPlanEntry.day)
        .all()
    )
    by_day = {e.day: e for e in entries}
    out = []
    for day in range(1, 6):  # Mon=1 .. Fri=5
        if day in by_day:
            out.append(by_day[day])
        else:
            row = MealPlanEntry(year=y, week=w, day=day, dinner="")
            db.add(row)
            db.commit()
            db.refresh(row)
            out.append(row)
    return out


@router.put("/slot", response_model=MealPlanEntryOut)
def set_day(
    year: int = Query(..., description="ISO year"),
    week: int = Query(..., ge=1, le=53),
    day: int = Query(..., ge=1, le=5, description="1=Mon .. 5=Fri"),
    data: MealPlanDayUpdate = ...,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    row = (
        db.query(MealPlanEntry)
        .filter(MealPlanEntry.year == year, MealPlanEntry.week == week, MealPlanEntry.day == day)
        .first()
    )
    if not row:
        row = MealPlanEntry(year=year, week=week, day=day, dinner=data.dinner, recipe_id=data.recipe_id, recipe_servings=data.recipe_servings)
        db.add(row)
    else:
        row.dinner = data.dinner
        if data.recipe_id is not None:
            row.recipe_id = data.recipe_id
        if data.recipe_servings is not None:
            row.recipe_servings = data.recipe_servings
    db.commit()
    db.refresh(row)
    return row
