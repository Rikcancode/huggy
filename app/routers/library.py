import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import LibraryItem, User
from app.schemas import LibraryItemCreate, LibraryItemUpdate, LibraryItemOut
from app.auth import get_current_user, require_admin
from app.config import settings

UPLOAD_DIR = Path(settings.upload_dir) if settings.upload_dir else Path(__file__).resolve().parent.parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB

router = APIRouter(prefix="/api/library", tags=["library"])


@router.get("", response_model=list[LibraryItemOut])
def list_items(
    category_id: int | None = None,
    q: str | None = Query(None, description="Search by name"),
    db: Session = Depends(get_db),
):
    query = db.query(LibraryItem).options(joinedload(LibraryItem.category))
    if category_id:
        query = query.filter(LibraryItem.category_id == category_id)
    if q:
        query = query.filter(LibraryItem.name.ilike(f"%{q}%"))
    return query.order_by(LibraryItem.name).all()


@router.get("/{item_id}", response_model=LibraryItemOut)
def get_item(item_id: int, db: Session = Depends(get_db)):
    item = db.query(LibraryItem).options(joinedload(LibraryItem.category)).get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    return item


@router.post("", response_model=LibraryItemOut, status_code=201)
def create_item(data: LibraryItemCreate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    existing = db.query(LibraryItem).filter(LibraryItem.name.ilike(data.name)).first()
    if existing:
        raise HTTPException(409, f"Item '{data.name}' already exists (id={existing.id})")
    item = LibraryItem(**data.model_dump())
    db.add(item)
    db.commit()
    db.refresh(item)
    return item


@router.put("/{item_id}", response_model=LibraryItemOut)
def update_item(item_id: int, data: LibraryItemUpdate, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(LibraryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.post("/{item_id}/image", response_model=LibraryItemOut)
async def upload_image(
    item_id: int,
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    item = db.query(LibraryItem).options(joinedload(LibraryItem.category)).get(item_id)
    if not item:
        raise HTTPException(404, "Item not found")

    ext = Path(file.filename or "").suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(400, f"File type {ext} not allowed. Use: {', '.join(ALLOWED_EXTENSIONS)}")

    contents = await file.read()
    if len(contents) > MAX_FILE_SIZE:
        raise HTTPException(400, "File too large (max 5 MB)")

    filename = f"{uuid.uuid4().hex}{ext}"
    (UPLOAD_DIR / filename).write_bytes(contents)

    if item.image_url and item.image_url.startswith("/uploads/"):
        old_file = UPLOAD_DIR / Path(item.image_url).name
        old_file.unlink(missing_ok=True)

    item.image_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(item)
    return item


@router.delete("/{item_id}/image", status_code=204)
def delete_image(item_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(LibraryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if item.image_url and item.image_url.startswith("/uploads/"):
        old_file = UPLOAD_DIR / Path(item.image_url).name
        old_file.unlink(missing_ok=True)
    item.image_url = None
    db.commit()


@router.delete("/{item_id}", status_code=204)
def delete_item(item_id: int, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    item = db.get(LibraryItem, item_id)
    if not item:
        raise HTTPException(404, "Item not found")
    if item.image_url and item.image_url.startswith("/uploads/"):
        old_file = UPLOAD_DIR / Path(item.image_url).name
        old_file.unlink(missing_ok=True)
    db.delete(item)
    db.commit()
