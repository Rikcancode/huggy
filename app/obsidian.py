"""
Obsidian Local REST API client and recipe markdown parser.
Set GROCERY_OBSIDIAN_API_URL and optionally GROCERY_OBSIDIAN_API_KEY.
"""
import re
from urllib.parse import quote
import httpx
from app.config import settings


def _client() -> httpx.Client | None:
    if not settings.obsidian_api_url:
        return None
    base = settings.obsidian_api_url.rstrip("/")
    headers = {}
    if settings.obsidian_api_key:
        headers["Authorization"] = f"Bearer {settings.obsidian_api_key}"
    return httpx.Client(base_url=base, headers=headers, timeout=15.0, verify=False)


def obsidian_available() -> bool:
    try:
        with _client() as c:
            if c is None:
                return False
            r = c.get("/")
            return r.is_success
    except Exception:
        return False


def obsidian_get_file(vault_path: str) -> str | None:
    """Read a vault file. Path is relative to vault root, e.g. 'Recipes/Pasta.md'."""
    try:
        with _client() as c:
            if c is None:
                return None
            # Obsidian vault paths can contain spaces / emoji; URL-encode each segment.
            encoded_path = "/".join(quote(seg, safe="") for seg in vault_path.split("/"))
            r = c.get(f"/vault/{encoded_path}")
            if r.status_code != 200:
                return None
            return r.text
    except Exception:
        return None


def obsidian_search(query: str) -> list[dict] | None:
    """Simple text search. Returns list of matches (structure depends on API)."""
    try:
        with _client() as c:
            if c is None:
                return None
            r = c.post("/search/simple/", json={"query": query})
            if r.status_code != 200:
                return None
            return r.json()
    except Exception:
        return None


def obsidian_list_folder(path: str = "") -> list[str] | None:
    """List vault root or folder. Use trailing slash for folder: 'Recipes/'."""
    try:
        with _client() as c:
            if c is None:
                return None
            if not path:
                url = "/vault/"
            else:
                trailing_slash = path.endswith("/")
                raw = path.rstrip("/")
                encoded_path = "/".join(quote(seg, safe="") for seg in raw.split("/") if seg)
                url = "/vault/" + encoded_path + "/"
            r = c.get(url)
            if r.status_code != 200:
                return None
            data = r.json()
            # Obsidian API returns {"files": [...]} — extract the list
            return data.get("files") if isinstance(data, dict) else data
    except Exception:
        return None


# ---- Recipe parsing from markdown ----
# Matches lines like:
# - "- 180 grams butter"
# - "- 3 eggs"
# - "- 1/2 cup flour"
# - "- salt to taste" (no leading quantity; returned as quantity=1)
_ING_LINE = re.compile(
    r"^\s*[-*]\s*"
    # Optional leading quantity (supports decimals and simple fractions: 1/2, 1.5/2)
    r"(?:(?P<qty>[0-9]+(?:\.[0-9]+)?(?:\s*/\s*[0-9]+(?:\.[0-9]+)?)?)\s*)?"
    # Optional unit right after quantity
    r"(?:(?P<unit>(?:grams?|g|kg|ml|milliliters?|liters?|l|cup|cups|tbsp|tablespoons?|tsp|teaspoons?|oz|ounces?|cloves?|pinch|pieces?|slices?|cans?|bunches?|sprigs?|to taste))\s*)?"
    # Remaining text is the ingredient name
    r"(?P<name>.+?)\s*$",
    re.IGNORECASE,
)


def parse_ingredient_line(line: str) -> dict | None:
    """Parse one ingredient line. Returns {'name': str, 'quantity': float, 'unit': str} or None."""
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    # Strip leading - or *
    stripped = line.lstrip("-*").strip()
    m = _ING_LINE.match(line)
    if m:
        qty_str = m.group("qty")
        unit = (m.group("unit") or "unit").strip()
        name = (m.group("name") or "").strip()

        # Quantity is optional in Obsidian notes (e.g. "- Oregano").
        # When missing, treat as 1 unit (unit will typically be "unit").
        if not qty_str:
            qty = 1.0
        elif "/" in qty_str:
            a, b = qty_str.split("/", 1)
            qty = float(a.strip()) / float(b.strip())
        else:
            qty = float(qty_str)
        if not name:
            return None
        return {"name": name, "quantity": qty, "unit": unit}
    # No quantity: "salt to taste" or "some butter"
    if stripped:
        return {"name": stripped, "quantity": 1.0, "unit": "unit"}
    return None


def parse_recipe_markdown(md: str, title: str | None = None) -> dict | None:
    """
    Parse markdown recipe. Expects ## Ingredients with bullet list.
    Returns dict: name, default_servings (4), ingredients list, directions (optional).
    """
    lines = md.replace("\r\n", "\n").split("\n")
    in_ingredients = False
    in_directions = False
    ingredients = []
    directions_lines = []
    name = title or "Untitled"

    source_url: str | None = None
    # Try YAML frontmatter for title/servings/source
    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            stripped_line = lines[i].strip()
            key_lower = stripped_line.lower()
            if key_lower.startswith("title:"):
                name = lines[i].split(":", 1)[1].strip().strip("'\"").strip()
            elif key_lower.startswith("source:") or key_lower.startswith("url:") or key_lower.startswith("source_url:"):
                val = lines[i].split(":", 1)[1].strip().strip("'\"").strip()
                if val.startswith("http"):
                    source_url = val
            elif key_lower.startswith("servings:"):
                pass  # could set default_servings from here
            i += 1
        lines = lines[i + 1 :]  # skip frontmatter

    for line in lines:
        stripped = line.strip()
        if re.match(r"^#+\s+", stripped):
            in_ingredients = "ingredient" in stripped.lower()
            in_directions = "direction" in stripped.lower() or "instruction" in stripped.lower() or "step" in stripped.lower()
            if in_directions and not in_ingredients:
                directions_lines.append(line)
            continue
        if in_ingredients and (stripped.startswith("-") or stripped.startswith("*")):
            ing = parse_ingredient_line(line)
            if ing:
                ingredients.append(ing)
        elif in_directions:
            directions_lines.append(line)

    if not ingredients and not name:
        return None
    return {
        "name": name,
        "default_servings": 4,
        "source_url": source_url,
        "ingredients": ingredients,
        "directions": "\n".join(directions_lines).strip() or None,
    }
