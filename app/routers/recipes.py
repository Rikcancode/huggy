"""
Recipes: CRUD, Obsidian sync, ratings, add ingredients to list, week aggregation.
"""
from datetime import date
import time
import uuid
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, Query, Body, UploadFile, File
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func

from app.database import get_db
from app.models import Recipe, RecipeRating, MealPlanEntry, LibraryItem, GroceryListItem, GroceryList
from app.schemas import (
    RecipeOut,
    RecipeCreate,
    RecipeUpdate,
    RecipeRatingUpdate,
    RecipeIngredient,
    RecipeNutrition,
    ObsidianSyncFolderResult,
    WeekIngredientItem,
)
from app.auth import get_current_user
from app.obsidian import obsidian_available, obsidian_get_file, obsidian_list_folder, parse_recipe_markdown
from app.config import settings

router = APIRouter(prefix="/api/recipes", tags=["recipes"])
_last_obsidian_auto_sync_ts: float = 0.0


def _recipe_to_out(r: Recipe, user_id: int | None, db: Session) -> RecipeOut:
    ratings = db.query(RecipeRating).filter(RecipeRating.recipe_id == r.id).all()
    avg = (sum(x.rating for x in ratings) / len(ratings)) if ratings else None
    user_rating = next((x.rating for x in ratings if x.user_id == user_id), None)
    nutrition = RecipeNutrition(**r.nutrition) if isinstance(r.nutrition, dict) else None
    raw_tags = r.tags
    tags = raw_tags if isinstance(raw_tags, list) else []
    return RecipeOut(
        id=r.id,
        name=r.name,
        source_path=r.source_path,
        source_url=r.source_url,
        thumbnail_url=r.thumbnail_url,
        recipe_type=r.recipe_type,
        nutrition=nutrition,
        kid_friendly=r.kid_friendly,
        prep_time_minutes=r.prep_time_minutes,
        cooking_time_minutes=r.cooking_time_minutes,
        oven_temp_celsius=r.oven_temp_celsius,
        oven_duration_minutes=r.oven_duration_minutes,
        oven_mode=r.oven_mode,
        tags=tags,
        default_servings=r.default_servings,
        ingredients=[RecipeIngredient(**x) for x in (r.ingredients or [])],
        directions=r.directions,
        created_at=r.created_at,
        updated_at=r.updated_at,
        rating_avg=round(avg, 1) if avg is not None else None,
        rating_count=len(ratings),
        user_rating=user_rating,
    )


@router.get("", response_model=list[RecipeOut])
def list_recipes(
    q: str | None = Query(None, description="Search name"),
    tag: str | None = Query(None, description="Filter by tag (e.g. 'meat')"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Keep DB in sync with Obsidian so current + future recipes are searchable
    # without manually entering note paths in the UI.
    if settings.obsidian_recipes_auto_sync and obsidian_available():
        folder = (settings.obsidian_recipes_folder or "").strip()
        if folder:
            now = time.time()
            global _last_obsidian_auto_sync_ts
            interval = max(10, settings.obsidian_recipes_sync_interval_seconds)
            should_sync = (now - _last_obsidian_auto_sync_ts) >= interval
            if should_sync:
                # Best-effort auto-sync; if it fails, continue serving DB results.
                try:
                    sync_from_obsidian_folder(
                        path=folder,
                        recursive=True,
                        max_files=settings.obsidian_recipes_max_files,
                        user=user,
                        db=db,
                    )
                    _last_obsidian_auto_sync_ts = now
                except HTTPException:
                    pass

    query = db.query(Recipe)
    if q:
        query = query.filter(Recipe.name.ilike(f"%{q}%"))
    recipes = query.order_by(Recipe.name).all()
    out = [_recipe_to_out(r, user.id, db) for r in recipes]
    # Tag filtering is done in Python since tags are stored as JSON in SQLite.
    if tag:
        out = [r for r in out if tag.lower() in [t.lower() for t in r.tags]]
    return out


@router.get("/obsidian-available")
def check_obsidian(user=Depends(get_current_user)):
    return {"available": obsidian_available()}


@router.get("/obsidian-list")
def obsidian_list(
    path: str = Query("", description="Folder path, e.g. Recipes/"),
    user=Depends(get_current_user),
):
    if not obsidian_available():
        raise HTTPException(503, "Obsidian API not configured or unreachable")
    result = obsidian_list_folder(path)
    if result is None:
        raise HTTPException(502, "Failed to list Obsidian vault")
    return {"paths": result}


@router.post("/sync-obsidian", response_model=RecipeOut)
def sync_from_obsidian(
    path: str = Query(..., description="Vault path to .md file"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not obsidian_available():
        raise HTTPException(503, "Obsidian API not configured or unreachable")
    raw = obsidian_get_file(path)
    if not raw:
        raise HTTPException(404, "File not found or unreadable")
    parsed = parse_recipe_markdown(raw)
    if not parsed or not parsed.get("ingredients"):
        raise HTTPException(400, "Could not parse recipe (no ingredients section?)")
    existing = db.query(Recipe).filter(Recipe.source_path == path).first()
    if existing:
        existing.name = parsed["name"]
        existing.default_servings = parsed.get("default_servings", 4)
        existing.ingredients = parsed["ingredients"]
        existing.directions = parsed.get("directions")
        db.commit()
        db.refresh(existing)
        return _recipe_to_out(existing, user.id, db)
    recipe = Recipe(
        name=parsed["name"],
        source_path=path,
        default_servings=parsed.get("default_servings", 4),
        ingredients=parsed["ingredients"],
        directions=parsed.get("directions"),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _recipe_to_out(recipe, user.id, db)


def _normalize_obsidian_relpath(p: str) -> str:
    # API expects vault-relative paths, without a leading slash.
    return p.lstrip("/")


def _join_folder_and_entry(folder: str, entry: str) -> str:
    """
    Join a folder path (vault-relative, no leading slash) and a listing entry.

    Obsidian may return entries as either:
    - full relative paths (containing "/"), or
    - just names (no "/") inside the folder.
    """
    folder = _normalize_obsidian_relpath(folder).rstrip("/")
    entry = _normalize_obsidian_relpath(entry)
    if not entry:
        return folder
    # Only treat entry as a full path if "/" appears before the trailing slash
    if "/" in entry.rstrip("/"):
        return entry
    if folder:
        return f"{folder}/{entry}"
    return entry


def _upsert_recipe_from_obsidian_path(
    *,
    db: Session,
    vault_path: str,
) -> tuple[bool, bool, str | None]:
    """
    Upsert a single Obsidian note into the recipes table.

    Returns (success, was_update, error_message_if_any).
    "success" is false for parse failures / no ingredients.
    """
    raw = obsidian_get_file(vault_path)
    if not raw:
        return False, False, "File not found or unreadable"
    filename = vault_path.split("/")[-1]
    title_from_filename = filename[:-3] if filename.lower().endswith(".md") else filename
    parsed = parse_recipe_markdown(raw, title=title_from_filename)
    if not parsed or not parsed.get("ingredients"):
        return False, False, "Could not parse recipe (no ingredients section?)"

    existing = db.query(Recipe).filter(Recipe.source_path == vault_path).first()
    was_update = existing is not None
    if existing:
        existing.name = parsed["name"]
        existing.default_servings = parsed.get("default_servings", 4)
        existing.ingredients = parsed["ingredients"]
        existing.directions = parsed.get("directions")
        if parsed.get("source_url"):
            existing.source_url = parsed["source_url"]
        db.commit()
        return True, was_update, None

    recipe = Recipe(
        name=parsed["name"],
        source_path=vault_path,
        source_url=parsed.get("source_url"),
        default_servings=parsed.get("default_servings", 4),
        ingredients=parsed["ingredients"],
        directions=parsed.get("directions"),
    )
    db.add(recipe)
    db.commit()
    return True, was_update, None


# GET + POST: some clients (cached UI, browser prefetch) hit this with GET; without GET,
# FastAPI matches GET /api/recipes/sync-obsidian-folder to GET /{recipe_id} → 422.
@router.get("/sync-obsidian-folder", response_model=ObsidianSyncFolderResult)
@router.post("/sync-obsidian-folder", response_model=ObsidianSyncFolderResult)
def sync_from_obsidian_folder(
    path: str = Query(..., description="Vault folder path, e.g. Family/Recipes/"),
    recursive: bool = Query(True, description="Recurse into nested subfolders"),
    max_files: int = Query(1000, ge=1, le=50000, description="Safety limit for discovered notes"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Sync all Obsidian recipe notes under a folder into the app DB.

    This enables `GET /api/recipes?q=...` to find recipes by name.
    """
    if not obsidian_available():
        raise HTTPException(503, "Obsidian API not configured or unreachable")

    folder = _normalize_obsidian_relpath(path)
    folder = folder.rstrip("/")
    if not folder:
        raise HTTPException(400, "Folder path is required")

    synced = 0
    updated = 0
    skipped = 0
    failed: list[dict] = []

    # BFS traversal to avoid deep recursion.
    queue: list[str] = [folder]
    visited: set[str] = set()
    discovered_files = 0

    while queue and discovered_files < max_files:
        current = queue.pop(0)
        if current in visited:
            continue
        visited.add(current)

        entries = obsidian_list_folder(current + "/")
        if not entries:
            continue

        for entry in entries:
            # Normalize listing entry to a usable vault-relative path
            # (keep directory trailing slash if present).
            if isinstance(entry, str):
                full_path = _join_folder_and_entry(current, entry)
            elif isinstance(entry, dict):
                full_path = _join_folder_and_entry(current, str(entry.get("path") or entry.get("name") or ""))
            else:
                continue

            if not full_path:
                continue

            # Directories are expected to be returned with a trailing '/' by the Obsidian plugin.
            is_dir = full_path.endswith("/")
            full_path_norm = full_path.rstrip("/")

            if is_dir:
                if recursive:
                    queue.append(full_path_norm)
                continue

            # Only sync markdown notes.
            if not full_path_norm.lower().endswith(".md"):
                skipped += 1
                continue

            discovered_files += 1
            ok, was_update, err = _upsert_recipe_from_obsidian_path(db=db, vault_path=full_path_norm)
            if ok:
                synced += 1
                if was_update:
                    updated += 1
            else:
                failed.append({"path": full_path_norm, "error": err or "Unknown error"})

    # Normalize "updated": if we couldn't approximate well, still provide synced count.
    # But the UI consumer can rely on `synced` as the main metric.
    return ObsidianSyncFolderResult(synced=synced, updated=updated, skipped=skipped, failed=failed)


@router.get("/{recipe_id}", response_model=RecipeOut)
def get_recipe(
    recipe_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    return _recipe_to_out(r, user.id, db)


@router.post("", response_model=RecipeOut, status_code=201)
def create_recipe(
    data: RecipeCreate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    nutrition = data.nutrition.model_dump() if data.nutrition else None
    recipe = Recipe(
        name=data.name,
        source_path=data.source_path,
        source_url=data.source_url,
        thumbnail_url=data.thumbnail_url,
        prep_time_minutes=data.prep_time_minutes,
        cooking_time_minutes=data.cooking_time_minutes,
        oven_temp_celsius=data.oven_temp_celsius,
        oven_duration_minutes=data.oven_duration_minutes,
        oven_mode=data.oven_mode,
        recipe_type=data.recipe_type,
        kid_friendly=data.kid_friendly,
        nutrition=nutrition,
        default_servings=data.default_servings,
        tags=data.tags or [],
        ingredients=[x.model_dump() for x in data.ingredients],
        directions=data.directions,
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _recipe_to_out(recipe, user.id, db)


@router.put("/{recipe_id}", response_model=RecipeOut)
def update_recipe(
    recipe_id: int,
    data: RecipeUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    if data.name is not None:
        r.name = data.name
    if data.source_url is not None:
        r.source_url = data.source_url or None
    if data.thumbnail_url is not None:
        r.thumbnail_url = data.thumbnail_url or None
    if data.default_servings is not None:
        r.default_servings = data.default_servings
    if data.prep_time_minutes is not None:
        r.prep_time_minutes = data.prep_time_minutes
    if data.cooking_time_minutes is not None:
        r.cooking_time_minutes = data.cooking_time_minutes
    if data.oven_temp_celsius is not None:
        r.oven_temp_celsius = data.oven_temp_celsius
    if data.oven_duration_minutes is not None:
        r.oven_duration_minutes = data.oven_duration_minutes
    if data.oven_mode is not None:
        r.oven_mode = data.oven_mode or None
    if data.tags is not None:
        r.tags = data.tags
    if data.ingredients is not None:
        r.ingredients = [x.model_dump() for x in data.ingredients]
    if data.directions is not None:
        r.directions = data.directions
    db.commit()
    db.refresh(r)
    return _recipe_to_out(r, user.id, db)


@router.delete("/{recipe_id}", status_code=204)
def delete_recipe(
    recipe_id: int,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    db.delete(r)
    db.commit()


_UPLOAD_DIR = Path(__file__).resolve().parent.parent.parent / "uploads"
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
_ALLOWED_IMG_EXTS = {".jpg", ".jpeg", ".png", ".webp", ".gif"}


@router.post("/{recipe_id}/image", response_model=RecipeOut)
async def upload_recipe_image(
    recipe_id: int,
    file: UploadFile = File(...),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Upload a thumbnail image for a recipe."""
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    ext = Path(file.filename or "").suffix.lower()
    if ext not in _ALLOWED_IMG_EXTS:
        raise HTTPException(400, f"Allowed: {', '.join(_ALLOWED_IMG_EXTS)}")
    contents = await file.read()
    if len(contents) > 8 * 1024 * 1024:
        raise HTTPException(400, "File too large (max 8 MB)")
    filename = f"recipe_{uuid.uuid4().hex}{ext}"
    (_UPLOAD_DIR / filename).write_bytes(contents)
    if r.thumbnail_url and r.thumbnail_url.startswith("/uploads/"):
        old = _UPLOAD_DIR / Path(r.thumbnail_url).name
        old.unlink(missing_ok=True)
    r.thumbnail_url = f"/uploads/{filename}"
    db.commit()
    db.refresh(r)
    return _recipe_to_out(r, user.id, db)


@router.post("/{recipe_id}/rate", response_model=RecipeOut)
def rate_recipe(
    recipe_id: int,
    data: RecipeRatingUpdate,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not (1 <= data.rating <= 5):
        raise HTTPException(400, "Rating must be 1-5")
    r = db.get(Recipe, recipe_id)
    if not r:
        raise HTTPException(404, "Recipe not found")
    existing = db.query(RecipeRating).filter(RecipeRating.recipe_id == recipe_id, RecipeRating.user_id == user.id).first()
    if existing:
        existing.rating = data.rating
    else:
        db.add(RecipeRating(recipe_id=recipe_id, user_id=user.id, rating=data.rating))
    db.commit()
    db.refresh(r)
    return _recipe_to_out(r, user.id, db)


def _match_library_item(db: Session, name: str):
    """Find library item by name (case-insensitive)."""
    n = name.strip()
    return db.query(LibraryItem).filter(func.lower(LibraryItem.name) == n.lower()).first()


@router.post("/{recipe_id}/add-to-list")
def add_recipe_to_list(
    recipe_id: int,
    list_id: int = Query(...),
    servings: int = Query(..., ge=1),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add recipe ingredients to a grocery list, scaled by servings. Matches by library item name."""
    recipe = db.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(404, "Recipe not found")
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")
    scale = servings / max(1, recipe.default_servings)
    added = []
    skipped = []
    for ing in recipe.ingredients or []:
        lib = _match_library_item(db, ing["name"])
        if not lib:
            skipped.append(ing["name"])
            continue
        qty = round(ing["quantity"] * scale, 2)
        existing = db.query(GroceryListItem).filter(
            GroceryListItem.list_id == list_id,
            GroceryListItem.library_item_id == lib.id,
            GroceryListItem.status == "pending",
        ).first()
        if existing:
            existing.quantity += qty
            added.append({"name": lib.name, "quantity": existing.quantity, "unit": ing.get("unit", "unit")})
        else:
            item = GroceryListItem(
                list_id=list_id,
                library_item_id=lib.id,
                quantity=qty,
                unit=ing.get("unit", "unit"),
                added_by_id=user.id,
                added_by_display_name=user.name,
            )
            db.add(item)
            added.append({"name": lib.name, "quantity": qty, "unit": item.unit})
    db.commit()
    return {"added": added, "skipped": skipped}


def _get_week_ingredients(db: Session, year: int, week: int) -> list[dict]:
    """Aggregate ingredients from all recipe slots in the week. Same ingredient merged (summed).
    Each result includes expiration_date (earliest meal day that uses the ingredient) and context."""
    entries = (
        db.query(MealPlanEntry)
        .filter(MealPlanEntry.year == year, MealPlanEntry.week == week, MealPlanEntry.recipe_id.isnot(None))
        .options(joinedload(MealPlanEntry.recipe))
        .all()
    )
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    merged = {}
    for e in entries:
        if not e.recipe or not e.recipe.ingredients:
            continue
        servings = e.recipe_servings or e.recipe.default_servings
        scale = servings / max(1, e.recipe.default_servings)
        meal_date = date.fromisocalendar(year, week, e.day)
        day_label = day_names[e.day - 1] if 1 <= e.day <= 7 else str(e.day)
        for ing in e.recipe.ingredients:
            key = (ing["name"].strip().lower(), ing.get("unit", "unit"))
            qty = ing["quantity"] * scale
            if key not in merged:
                merged[key] = {
                    "name": ing["name"].strip(),
                    "quantity": 0,
                    "unit": ing.get("unit", "unit"),
                    "expiration_date": meal_date,
                    "context": [f"{day_label}: {e.recipe.name}"],
                }
            else:
                if meal_date < merged[key]["expiration_date"]:
                    merged[key]["expiration_date"] = meal_date
                ctx = f"{day_label}: {e.recipe.name}"
                if ctx not in merged[key]["context"]:
                    merged[key]["context"].append(ctx)
            merged[key]["quantity"] += qty
    return [
        {
            "name": v["name"],
            "quantity": round(v["quantity"], 2),
            "unit": v["unit"],
            "expiration_date": v["expiration_date"].isoformat(),
            "context": v["context"],
        }
        for v in merged.values()
    ]


@router.get("/meal-plan/week-ingredients")
def get_week_ingredients(
    year: int = Query(...),
    week: int = Query(..., ge=1, le=53),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregated ingredients for the week (recipe slots only). Same ingredient appears once with summed quantity."""
    return _get_week_ingredients(db, year, week)


@router.post("/meal-plan/add-week-to-list")
def add_week_to_list(
    list_id: int = Query(...),
    year: int = Query(...),
    week: int = Query(..., ge=1, le=53),
    ingredients: list[WeekIngredientItem] | None = Body(None, description="Override: use this list (with expiration dates) instead of computed"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add week's ingredients to list. If ingredients body provided, use that (after user edit); else compute from meal plan."""
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")
    if ingredients is not None and len(ingredients) > 0:
        to_add = [{"name": x.name, "quantity": x.quantity, "unit": x.unit, "expiration_date": x.expiration_date} for x in ingredients]
    else:
        to_add = _get_week_ingredients(db, year, week)
    added = []
    skipped = []
    for ing in to_add:
        lib = _match_library_item(db, ing["name"])
        if not lib:
            skipped.append(ing["name"])
            continue
        qty = ing["quantity"]
        exp_str = ing.get("expiration_date")
        exp_date = None
        if exp_str:
            try:
                from datetime import date as _date
                exp_date = _date.fromisoformat(exp_str)
            except (ValueError, TypeError):
                exp_date = None
        existing = db.query(GroceryListItem).filter(
            GroceryListItem.list_id == list_id,
            GroceryListItem.library_item_id == lib.id,
            GroceryListItem.status == "pending",
        ).first()
        if existing:
            existing.quantity += qty
            # Use the earlier expiration date
            if exp_date and (existing.expiration_date is None or exp_date < existing.expiration_date):
                existing.expiration_date = exp_date
            added.append({"name": lib.name, "quantity": existing.quantity, "unit": ing.get("unit", "unit")})
        else:
            item = GroceryListItem(
                list_id=list_id,
                library_item_id=lib.id,
                quantity=qty,
                unit=ing.get("unit", "unit"),
                expiration_date=exp_date,
                added_by_id=user.id,
                added_by_display_name=user.name,
            )
            db.add(item)
            added.append({"name": lib.name, "quantity": qty, "unit": item.unit})
    db.commit()
    return {"added": added, "skipped": skipped}
