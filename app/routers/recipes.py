"""
Recipes: CRUD, Obsidian sync, ratings, add ingredients to list, week aggregation.
"""
from datetime import date
from fastapi import APIRouter, Depends, HTTPException, Query, Body
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
)
from app.auth import get_current_user
from app.obsidian import obsidian_available, obsidian_get_file, obsidian_list_folder, parse_recipe_markdown

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


def _recipe_to_out(r: Recipe, user_id: int | None, db: Session) -> RecipeOut:
    ratings = db.query(RecipeRating).filter(RecipeRating.recipe_id == r.id).all()
    avg = (sum(x.rating for x in ratings) / len(ratings)) if ratings else None
    user_rating = next((x.rating for x in ratings if x.user_id == user_id), None)
    return RecipeOut(
        id=r.id,
        name=r.name,
        source_path=r.source_path,
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
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    query = db.query(Recipe)
    if q:
        query = query.filter(Recipe.name.ilike(f"%{q}%"))
    recipes = query.order_by(Recipe.name).all()
    return [_recipe_to_out(r, user.id, db) for r in recipes]


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
    recipe = Recipe(
        name=data.name,
        source_path=data.source_path,
        default_servings=data.default_servings,
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
    if data.default_servings is not None:
        r.default_servings = data.default_servings
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
    """Aggregate ingredients from all recipe slots in the week. Same ingredient merged (summed)."""
    entries = (
        db.query(MealPlanEntry)
        .filter(MealPlanEntry.year == year, MealPlanEntry.week == week, MealPlanEntry.recipe_id.isnot(None))
        .options(joinedload(MealPlanEntry.recipe))
        .all()
    )
    merged = {}
    for e in entries:
        if not e.recipe or not e.recipe.ingredients:
            continue
        servings = e.recipe_servings or e.recipe.default_servings
        scale = servings / max(1, e.recipe.default_servings)
        for ing in e.recipe.ingredients:
            key = (ing["name"].strip().lower(), ing.get("unit", "unit"))
            qty = ing["quantity"] * scale
            if key not in merged:
                merged[key] = {"name": ing["name"].strip(), "quantity": 0, "unit": ing.get("unit", "unit")}
            merged[key]["quantity"] += qty
    return [{"name": v["name"], "quantity": round(v["quantity"], 2), "unit": v["unit"]} for v in merged.values()]


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
    ingredients: list[RecipeIngredient] | None = Body(None, description="Override: use this list instead of computed"),
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Add week's ingredients to list. If ingredients body provided, use that (after user edit); else compute from meal plan."""
    gl = db.get(GroceryList, list_id)
    if not gl:
        raise HTTPException(404, "List not found")
    if ingredients is not None and len(ingredients) > 0:
        to_add = [{"name": x.name, "quantity": x.quantity, "unit": x.unit} for x in ingredients]
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
