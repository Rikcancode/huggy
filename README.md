# Grocery List

A self-hosted grocery list manager with a web UI. Manage shopping lists, an item library with categories, expiration tracking, repurchase reminders, and supermarket aisle ordering.

## Features

- **Shopping Lists** — create lists, add items by name (fuzzy match), mark as purchased
- **Item Library** — 130+ pre-seeded items with emoji icons, categories, and translations (DA/IT/BG)
- **Expiration Calendar** — monthly calendar view showing items by expiration date, color-coded by urgency
- **Image Uploads** — attach photos to library items
- **Repurchase Reminders** — set recurring reminders for items you buy regularly
- **Supermarket Presets** — sort your list by aisle order for different stores
- **Recipe Library** — import recipes from any URL (Instagram, blogs, YouTube) with one click
- **Recipe URL Import** — paste an Instagram reel/post or recipe website URL; ingredients are extracted, converted to metric, and saved with nutrition estimates and kid-friendliness labels
- **API Key Auth** — separate admin and user keys
- **Duplicate Prevention** — adding an existing item returns an error or resets purchased items

## Recipe URL Import

Huggy can import recipes directly from a URL — Instagram reels/posts or any recipe website:

```
POST /api/recipes/import-url
{"url": "https://www.instagram.com/reel/..."}
```

**How it works:**

1. **Instagram URLs** (`instagram.com/reel/` or `/p/`) are scraped via [Apify](https://apify.com) — caption, thumbnail, and any linked recipe page are all extracted.
2. **All other URLs** are scraped via [Firecrawl](https://firecrawl.dev) (if configured) or a direct HTTP request.
3. Content is sent to **Gemini** (Google AI), which structures the recipe: ingredients are converted to metric, nutrition per serving is estimated, recipe type (`main`, `dessert`, `starter`, `breakfast`, `snacks`) and kid-friendliness are labelled.
4. The recipe is saved to the database and immediately available in the recipe library.

**Required environment variables:**

| Variable | Description |
|---|---|
| `GROCERY_GEMINI_API_KEY` | Google AI API key — used for recipe parsing (required) |
| `GROCERY_APIFY_API_TOKEN` | Apify token — required for Instagram URLs |
| `GROCERY_FIRECRAWL_API_KEY` | Firecrawl key — recommended for recipe websites; falls back to direct fetch |

## Quick Start (Docker)

```bash
docker compose up -d
```

The app will be available at `http://localhost:8089`.

Default API keys (change in `docker-compose.yml` or via environment variables):
- **Admin:** `grocery-admin-key-2026`
- **User:** `grocery-user-key-2026`

## Configuration

All settings are configured via environment variables (prefix `GROCERY_`):

| Variable | Default | Description |
|---|---|---|
| `GROCERY_DATABASE_URL` | `sqlite:////data/grocery.db` | Database connection string |
| `GROCERY_UPLOAD_DIR` | `/data/uploads` | Directory for uploaded images |
| `GROCERY_ADMIN_API_KEY` | `admin-change-me` | Admin API key |
| `GROCERY_USER_API_KEY` | `user-change-me` | User API key |
| `GROCERY_SEED_ON_STARTUP` | `true` | Seed the database with default items on first run |

## ZimaOS / CasaOS

**Use `docker-compose.yml` only** — do not paste the separate zimaos-app.yaml file (it is not valid compose). **Do you need a YAML that points to a GitHub repo?**  
Only if the store supports “Install from URL” or “Add from repository” and expects a manifest. Otherwise you don’t.

The compose uses `docker.io/rikcodes/huggy:ebba2d0`. Use **ebba2d0 or later** for Admin/mechou login (earlier tags like 79db995 have auth but no default password). The image is built and pushed by GitHub Actions on every push to `main` (repo secrets `DOCKER_USERNAME` and `DOCKER_PASSWORD`). If the tag is not on Docker Hub, build and push locally: `docker build -t rikcodes/huggy:ebba2d0 . && docker push rikcodes/huggy:ebba2d0`.

**Install:** Apps → Install a customized app → paste `docker-compose.yml` (or use its raw URL). Data is stored in `/DATA/AppData/huggy/data`.

**Web login:** Username **Admin**, password **mechou** (override with `GROCERY_DEFAULT_ADMIN_PASSWORD`).

**Troubleshooting**
- **"repository does not exist" for `grocery-list`** — The image name must be **`rikcodes/huggy`**, not `grocery-list`. In ZimaOS edit the app and set the image to `docker.io/rikcodes/huggy:ebba2d0` (or use the image you built yourself, see below).
- **"No module named 'app.routers.auth'"** — The container was built from an old or incomplete image that doesn’t include the auth router. You must use an image built from the current GitHub repo (see **Build the image yourself** below).
- **"Invalid credentials" with Admin/mechou** — Use an image built from commit **ebba2d0 or later** (that’s when the default password was added). Build from repo (see below) if the tag isn’t on Docker Hub.
- **"manifest for rikcodes/huggy:latest not found"** — That tag isn’t on Docker Hub (e.g. GitHub Actions not pushing). Build and push the image yourself, or build and run it on the server (see below).

**Build the image yourself (when Docker Hub tags are missing or wrong)**  
On the ZimaOS box (or any machine with Docker and git), run:

```bash
git clone https://github.com/Rikcancode/huggy.git
cd huggy
docker build -t rikcodes/huggy:ebba2d0 .
```

Then either:

- **A) Run it directly** (no ZimaOS app):  
  `docker run -d --name huggy -p 8089:8089 -v /DATA/AppData/huggy/data:/data -e GROCERY_DATABASE_URL=sqlite:////data/grocery.db -e GROCERY_UPLOAD_DIR=/data/uploads -e GROCERY_SEED_ON_STARTUP=true -e GROCERY_DEFAULT_ADMIN_PASSWORD=mechou rikcodes/huggy:ebba2d0`

- **B) Use it in ZimaOS:** In the app’s compose, set the image to `rikcodes/huggy:ebba2d0`. ZimaOS will use the image you just built (no pull). If the app is on another machine, push first: `docker push rikcodes/huggy:ebba2d0` (after `docker login`).

**Option 2 — Install from GitHub**  
1. Repo: **https://github.com/Rikcancode/huggy**  
2. If the store has “Install from URL” or “Add from repository”, use that URL.  
3. If it asks for a compose URL, use: `https://raw.githubusercontent.com/Rikcancode/huggy/main/docker-compose.yml`  
4. The repo’s `docker-compose.yml` includes an `x-casaos` block so ZimaOS shows the app name and port correctly.

## API

The full API is available at `http://localhost:8089/docs` (Swagger UI).

Key endpoints:

- `GET /api/lists` — list all grocery lists
- `GET /api/lists/{id}` — get list with items
- `POST /api/lists/{id}/items/by-name?name=Bananas` — add item by name
- `PATCH /api/lists/{id}/items/{item_id}/purchase` — mark purchased
- `GET /api/lists/expirations?month=3&year=2026` — items expiring in a month
- `GET /api/library` — browse item library
- `POST /api/library/{id}/image` — upload image for an item
- `GET /api/reminders/due` — check due reminders

### OpenClaw / automation

The API works with OpenClaw or any HTTP client. All requests that change data require the **`X-API-Key`** header (user or admin key). To record **who** performed an action (e.g. which OpenClaw user added or purchased an item), send **`X-User-Name`** with the display name (e.g. `Rik`); it is stored as “added by” / “purchased by” and in the activity log.

| What you want to do | Endpoint | Auth |
|---------------------|----------|------|
| **See lists** | `GET /api/lists` | None |
| **See what’s on a list** | `GET /api/lists/{id}` | None |
| **Add item by name** | `POST /api/lists/{id}/items/by-name?name=Bananas` | Required |
| **Create a list** | `POST /api/lists` body `{"name":"Grocery"}` | Required |
| **Mark item purchased** | `PATCH /api/lists/{id}/items/{item_id}/purchase` | Required |
| **Remove item** | `DELETE /api/lists/{id}/items/{item_id}` | Required |
| **Update item (qty, unit)** | `PUT /api/lists/{id}/items/{item_id}` body `{"quantity":2,"unit":"kg"}` | Required |

Example (add to list 1, user key):

```bash
curl -X POST "http://localhost:8089/api/lists/1/items/by-name?name=Milk" \
  -H "X-API-Key: grocery-user-key-2026"
```

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Uvicorn
- **Database:** SQLite (default) or PostgreSQL
- **Frontend:** Single-page admin panel (vanilla JS)
