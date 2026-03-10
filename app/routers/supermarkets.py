from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import SupermarketPreset, User
from app.schemas import SupermarketPresetCreate, SupermarketPresetUpdate, SupermarketPresetOut
from app.auth import require_admin

router = APIRouter(prefix="/api/supermarkets", tags=["supermarkets"])


@router.get("", response_model=list[SupermarketPresetOut])
def list_presets(db: Session = Depends(get_db)):
    return db.query(SupermarketPreset).order_by(SupermarketPreset.name).all()


@router.get("/{preset_id}", response_model=SupermarketPresetOut)
def get_preset(preset_id: int, db: Session = Depends(get_db)):
    p = db.get(SupermarketPreset, preset_id)
    if not p:
        raise HTTPException(404, "Preset not found")
    return p


@router.post("", response_model=SupermarketPresetOut, status_code=201)
def create_preset(data: SupermarketPresetCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    p = SupermarketPreset(**data.model_dump())
    db.add(p)
    db.commit()
    db.refresh(p)
    return p


@router.put("/{preset_id}", response_model=SupermarketPresetOut)
def update_preset(preset_id: int, data: SupermarketPresetUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(SupermarketPreset, preset_id)
    if not p:
        raise HTTPException(404, "Preset not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(p, k, v)
    db.commit()
    db.refresh(p)
    return p


@router.delete("/{preset_id}", status_code=204)
def delete_preset(preset_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    p = db.get(SupermarketPreset, preset_id)
    if not p:
        raise HTTPException(404, "Preset not found")
    db.delete(p)
    db.commit()
