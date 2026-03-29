"""
Recipe URL importer: Instagram (Apify) or web (Firecrawl/httpx) → Gemini → DB.

POST /api/recipes/import-url  {"url": "https://..."}
"""
import json
import re

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.models import Recipe
from app.routers.recipes import _recipe_to_out
from app.schemas import RecipeOut

router = APIRouter(prefix="/api/recipes", tags=["recipes"])


class ImportUrlRequest(BaseModel):
    url: str


def _is_instagram(url: str) -> bool:
    return "instagram.com" in url


def _fetch_instagram(url: str) -> dict:
    if not settings.apify_api_token:
        raise HTTPException(503, "GROCERY_APIFY_API_TOKEN not configured")
    resp = httpx.post(
        "https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items"
        f"?token={settings.apify_api_token}&timeout=90",
        json={"directUrls": [url], "resultsType": "posts", "resultsLimit": 1},
        timeout=120,
    )
    resp.raise_for_status()
    items = resp.json()
    if not items:
        raise HTTPException(422, "Apify returned no results for this Instagram URL")
    return items[0]


def _fetch_web(url: str) -> str:
    if settings.firecrawl_api_key:
        resp = httpx.post(
            "https://api.firecrawl.dev/v1/scrape",
            headers={"Authorization": f"Bearer {settings.firecrawl_api_key}"},
            json={"url": url, "formats": ["markdown"]},
            timeout=60,
        )
        if resp.is_success:
            data = resp.json()
            return data.get("data", {}).get("markdown") or data.get("markdown", "")
    resp = httpx.get(
        url,
        timeout=30,
        follow_redirects=True,
        headers={"User-Agent": "Mozilla/5.0 (compatible; HuggyBot/1.0)"},
    )
    resp.raise_for_status()
    return resp.text


def _extract_url_from_text(text: str) -> str | None:
    m = re.search(r'https?://\S+', text)
    return m.group(0).rstrip(".,)") if m else None


def _parse_with_gemini(content: str, source_url: str) -> dict:
    if not settings.gemini_api_key:
        raise HTTPException(503, "GROCERY_GEMINI_API_KEY not configured")

    import google.generativeai as genai  # lazy import — optional dependency
    genai.configure(api_key=settings.gemini_api_key)
    model = genai.GenerativeModel("gemini-2.0-flash")

    prompt = f"""Extract the recipe from the content below and return a JSON object.

Source: {source_url}

---
{content[:15000]}
---

Return ONLY valid JSON (no markdown fences), with this exact structure:
{{
  "name": "Recipe Name",
  "default_servings": 4,
  "prep_time_minutes": 15,
  "cooking_time_minutes": 30,
  "oven_temp_celsius": 180,
  "oven_duration_minutes": 25,
  "oven_mode": "ventilated",
  "recipe_type": "main",
  "kid_friendly": true,
  "directions": "Step-by-step instructions as a single string.",
  "ingredients": [
    {{"name": "Chicken breast", "quantity": 500, "unit": "g"}},
    {{"name": "Olive oil", "quantity": 30, "unit": "ml"}}
  ],
  "nutrition": {{
    "calories": 450,
    "protein": 35,
    "carbs": 20,
    "fats": 15
  }}
}}

Rules:
- recipe_type must be one of: main, dessert, starter, breakfast, snacks
- Convert ALL measurements to metric (g, ml, °C). Keep original in parentheses in directions if helpful.
- nutrition values are per serving (estimate from standard food composition tables)
- kid_friendly: consider spice level, allergens, texture
- prep_time_minutes: active preparation time (chopping, mixing) before cooking
- cooking_time_minutes: total active cooking/baking time
- oven_temp_celsius: set to null if recipe doesn't use an oven
- oven_duration_minutes: set to null if recipe doesn't use an oven
- oven_mode: "static" or "ventilated" (fan-assisted); set to null if no oven
- If no recipe is found in the content, return {{"error": "No recipe found"}}
"""

    response = model.generate_content(prompt)
    text = response.text.strip()
    text = re.sub(r'^```(?:json)?\s*', '', text)
    text = re.sub(r'\s*```$', '', text)

    try:
        data = json.loads(text)
    except json.JSONDecodeError as exc:
        raise HTTPException(422, f"Could not parse Gemini response as JSON: {exc}")

    if "error" in data:
        raise HTTPException(422, data["error"])

    return data


def _scrape_and_parse(url: str) -> tuple[dict, str | None]:
    """Scrape URL and parse with Gemini. Returns (parsed_dict, thumbnail_url)."""
    thumbnail_url: str | None = None
    if _is_instagram(url):
        post = _fetch_instagram(url)
        caption = post.get("caption") or ""
        thumbnail_url = post.get("displayUrl")
        external_url = post.get("externalUrl") or _extract_url_from_text(caption)
        if external_url:
            try:
                web_content = _fetch_web(external_url)
                content = f"Instagram caption:\n{caption}\n\nLinked page:\n{web_content}"
            except Exception:
                content = caption
        else:
            content = caption
    else:
        content = _fetch_web(url)
    parsed = _parse_with_gemini(content, url)
    return parsed, thumbnail_url


@router.post("/import-url/preview")
def preview_recipe_import(
    body: ImportUrlRequest,
    user=Depends(get_current_user),
):
    """Scrape and parse a recipe URL without saving. Returns preview data for user review."""
    url = body.url.strip()
    parsed, thumbnail_url = _scrape_and_parse(url)
    ingredients = [
        {"name": ing["name"], "quantity": float(ing["quantity"]), "unit": ing.get("unit", "unit")}
        for ing in (parsed.get("ingredients") or [])
        if ing.get("name")
    ]
    if not ingredients:
        raise HTTPException(422, "No ingredients could be extracted from the recipe")
    return {
        "name": parsed.get("name") or "Imported Recipe",
        "source_url": url,
        "thumbnail_url": thumbnail_url,
        "default_servings": int(parsed.get("default_servings") or 4),
        "prep_time_minutes": parsed.get("prep_time_minutes"),
        "cooking_time_minutes": parsed.get("cooking_time_minutes"),
        "oven_temp_celsius": parsed.get("oven_temp_celsius"),
        "oven_duration_minutes": parsed.get("oven_duration_minutes"),
        "oven_mode": parsed.get("oven_mode"),
        "recipe_type": parsed.get("recipe_type"),
        "nutrition": parsed.get("nutrition"),
        "kid_friendly": parsed.get("kid_friendly"),
        "tags": [],
        "ingredients": ingredients,
        "directions": parsed.get("directions"),
    }


@router.post("/import-url", response_model=RecipeOut, status_code=201)
def import_recipe_from_url(
    body: ImportUrlRequest,
    user=Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Import a recipe from a URL and save it to the database.

    - **Instagram** (`instagram.com/reel/` or `/p/`) — scraped via Apify
      (requires `GROCERY_APIFY_API_TOKEN`). If the caption links to an external
      recipe page, that page is also scraped and merged.
    - **All other URLs** — scraped via Firecrawl if `GROCERY_FIRECRAWL_API_KEY`
      is set, otherwise via a plain HTTP request.
    - Content is structured by Gemini (`GROCERY_GEMINI_API_KEY`): ingredients are
      converted to metric, nutrition per serving is estimated, recipe type and
      kid-friendliness are labelled.
    """
    url = body.url.strip()
    parsed, thumbnail_url = _scrape_and_parse(url)

    ingredients = [
        {"name": ing["name"], "quantity": float(ing["quantity"]), "unit": ing.get("unit", "unit")}
        for ing in (parsed.get("ingredients") or [])
        if ing.get("name")
    ]
    if not ingredients:
        raise HTTPException(422, "No ingredients could be extracted from the recipe")

    recipe = Recipe(
        name=parsed.get("name") or "Imported Recipe",
        source_url=url,
        source_path=None,
        thumbnail_url=thumbnail_url,
        default_servings=int(parsed.get("default_servings") or 4),
        prep_time_minutes=parsed.get("prep_time_minutes"),
        cooking_time_minutes=parsed.get("cooking_time_minutes"),
        oven_temp_celsius=parsed.get("oven_temp_celsius"),
        oven_duration_minutes=parsed.get("oven_duration_minutes"),
        oven_mode=parsed.get("oven_mode"),
        recipe_type=parsed.get("recipe_type"),
        nutrition=parsed.get("nutrition"),
        kid_friendly=parsed.get("kid_friendly"),
        tags=[],
        ingredients=ingredients,
        directions=parsed.get("directions"),
    )
    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    return _recipe_to_out(recipe, user.id, db)
