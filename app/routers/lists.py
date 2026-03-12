from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session, joinedload
from app.database import get_db
from app.models import (
    GroceryList, GroceryListItem, LibraryItem, RepurchaseReminder, User,
    Category, SupermarketPreset,
)
from app.schemas import (
    GroceryListCreate, GroceryListUpdate, GroceryListOut,
    GroceryListSummary, GroceryListItemOut, RecentPurchaseOut,
    AddItemToList, UpdateListItem,
)
from app.auth import get_current_user

router = APIRouter(prefix="/api/lists", tags=["lists"])


@router.get("/recent-purchases", response_model=list[RecentPurchaseOut])
def get_recent_purchases(
    list_id: int | None = Query(None, description="Filter by list"),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db),
):
    """Return purchased items, most recent first. Used for Recent Purchases tab; expiration can be set here."""
    q = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .join(GroceryList)
        .filter(GroceryListItem.status == "purchased")
    )
    if list_id:
        q = q.filter(GroceryListItem.list_id == list_id)
    items = q.order_by(GroceryListItem.purchased_at.desc()).limit(limit).all()
    result = []
    for it in items:
        result.append(
            RecentPurchaseOut(
                list_id=it.list_id,
                list_name=it.grocery_list.name,
                item=it,
            )
        )
    return result


@router.get("/expirations", response_model=list[GroceryListItemOut])
def get_expirations(
    month: int | None = Query(None, ge=1, le=12),
    year: int | None = Query(None),
    db: Session = Depends(get_db),
):
    """Return all list items that have an expiration date, optionally filtered by month/year."""
    from datetime import date as date_cls
    q = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .filter(GroceryListItem.expiration_date.isnot(None))
    )
    if month and year:
        start = date_cls(year, month, 1)
        if month == 12:
            end = date_cls(year + 1, 1, 1)
        else:
            end = date_cls(year, month + 1, 1)
        q = q.filter(GroceryListItem.expiration_date >= start, GroceryListItem.expiration_date < end)
    return q.order_by(GroceryListItem.expiration_date).all()


@router.get("", response_model=list[GroceryListSummary])
def list_all(active_only: bool = False, db: Session = Depends(get_db)):
    q = db.query(GroceryList).options(joinedload(GroceryList.created_by))
    if active_only:
        q = q.filter(GroceryList.is_active.is_(True))
    lists = q.order_by(GroceryList.updated_at.desc()).all()
    results = []
    for gl in lists:
        count = db.query(GroceryListItem).filter(GroceryListItem.list_id == gl.id).count()
        summary = GroceryListSummary.model_validate(gl)
        summary.item_count = count
        results.append(summary)
    return results


@router.post("", response_model=GroceryListOut, status_code=201)
def create_list(data: GroceryListCreate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gl = GroceryList(name=data.name, created_by_id=user.id)
    db.add(gl)
    db.commit()
    db.refresh(gl)
    return gl


@router.get("/{list_id}", response_model=GroceryListOut)
def get_list(
    list_id: int,
    supermarket_id: int | None = Query(None, description="Sort by supermarket aisle order"),
    db: Session = Depends(get_db),
):
    gl = (
        db.query(GroceryList)
        .options(
            joinedload(GroceryList.created_by),
            joinedload(GroceryList.items).joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryList.items).joinedload(GroceryListItem.added_by),
            joinedload(GroceryList.items).joinedload(GroceryListItem.purchased_by),
        )
        .get(list_id)
    )
    if not gl:
        raise HTTPException(404, "List not found")

    if supermarket_id:
        preset = db.get(SupermarketPreset, supermarket_id)
        if preset and preset.category_order:
            order_map = {cid: idx for idx, cid in enumerate(preset.category_order)}
            gl.items.sort(
                key=lambda i: (
                    i.status != "pending",  # purchased items last
                    order_map.get(i.library_item.category_id, 999),
                    i.library_item.name,
                )
            )
    else:
        gl.items.sort(key=lambda i: (i.status != "pending", i.library_item.name))

    return gl


@router.put("/{list_id}", response_model=GroceryListOut)
def update_list(list_id: int, data: GroceryListUpdate, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(gl, k, v)
    db.commit()
    db.refresh(gl)
    return gl


@router.delete("/{list_id}", status_code=204)
def delete_list(list_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")
    db.delete(gl)
    db.commit()


# ---- List Items ----

@router.post("/{list_id}/items", response_model=GroceryListItemOut, status_code=201)
def add_item(list_id: int, data: AddItemToList, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")

    lib_item = db.get(LibraryItem, data.library_item_id)
    if not lib_item:
        raise HTTPException(404, "Library item not found")

    existing = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .filter_by(list_id=list_id, library_item_id=data.library_item_id)
        .first()
    )
    if existing:
        if existing.status == "purchased":
            existing.status = "pending"
            existing.quantity = data.quantity or lib_item.default_quantity
            existing.purchased_at = None
            existing.purchased_by_id = None
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(409, f"'{lib_item.name}' is already on this list")

    item = GroceryListItem(
        list_id=list_id,
        library_item_id=data.library_item_id,
        quantity=data.quantity or lib_item.default_quantity,
        unit=data.unit or lib_item.unit,
        added_by_id=user.id,
        expiration_date=data.expiration_date,
        notes=data.notes,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    # Reload with relationships for response
    item = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .get(item.id)
    )
    return item


@router.post("/{list_id}/items/by-name", response_model=GroceryListItemOut, status_code=201)
def add_item_by_name(
    list_id: int,
    name: str = Query(...),
    quantity: float | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add an item by name. Matches library items by name; creates a new library item if none match."""
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")

    name_clean = name.strip()
    if not name_clean:
        raise HTTPException(400, "Item name cannot be empty")

    lib_item = (
        db.query(LibraryItem)
        .filter(LibraryItem.name.ilike(name_clean))
        .first()
    )
    if not lib_item:
        lib_item = db.query(LibraryItem).filter(LibraryItem.name.ilike(f"%{name_clean}%")).first()
    if not lib_item:
        # Create new library item so users can add from list view without going to Library
        first_cat = db.query(Category).order_by(Category.sort_order).first()
        if not first_cat:
            raise HTTPException(400, "No categories defined; add a category first")
        lib_item = LibraryItem(
            name=name_clean,
            category_id=first_cat.id,
            default_quantity=1.0,
            unit="unit",
            created_by_id=user.id,
        )
        db.add(lib_item)
        db.flush()

    existing = (
        db.query(GroceryListItem)
        .filter_by(list_id=list_id, library_item_id=lib_item.id)
        .first()
    )
    if existing:
        if existing.status == "purchased":
            existing.status = "pending"
            existing.quantity = quantity or lib_item.default_quantity
            existing.purchased_at = None
            existing.purchased_by_id = None
            db.commit()
            db.refresh(existing)
            return existing
        raise HTTPException(409, f"'{lib_item.name}' is already on this list")

    item = GroceryListItem(
        list_id=list_id,
        library_item_id=lib_item.id,
        quantity=quantity or lib_item.default_quantity,
        unit=lib_item.unit,
        added_by_id=user.id,
    )
    db.add(item)
    db.commit()
    db.refresh(item)
    item = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .get(item.id)
    )
    return item


@router.put("/{list_id}/items/{item_id}", response_model=GroceryListItemOut)
def update_item(list_id: int, item_id: int, data: UpdateListItem, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .filter_by(id=item_id, list_id=list_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "List item not found")
    for k, v in data.model_dump(exclude_unset=True).items():
        setattr(item, k, v)
    db.commit()
    db.refresh(item)
    return item


@router.patch("/{list_id}/items/{item_id}/purchase", response_model=GroceryListItemOut)
def purchase_item(list_id: int, item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = (
        db.query(GroceryListItem)
        .options(
            joinedload(GroceryListItem.library_item).joinedload(LibraryItem.category),
            joinedload(GroceryListItem.added_by),
            joinedload(GroceryListItem.purchased_by),
        )
        .filter_by(id=item_id, list_id=list_id)
        .first()
    )
    if not item:
        raise HTTPException(404, "List item not found")

    item.status = "purchased"
    item.purchased_by_id = user.id
    item.purchased_at = datetime.utcnow()

    reminder = (
        db.query(RepurchaseReminder)
        .filter_by(library_item_id=item.library_item_id, active=True)
        .first()
    )
    if reminder:
        reminder.last_purchased = datetime.utcnow()
        reminder.next_due = datetime.utcnow() + timedelta(days=reminder.interval_days)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/{list_id}/items/{item_id}", status_code=204)
def remove_item(list_id: int, item_id: int, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    item = db.query(GroceryListItem).filter_by(id=item_id, list_id=list_id).first()
    if not item:
        raise HTTPException(404, "List item not found")
    db.delete(item)
    db.commit()
