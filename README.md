# Grocery List

A self-hosted grocery list manager with a web UI. Manage shopping lists, an item library with categories, expiration tracking, repurchase reminders, and supermarket aisle ordering.

## Features

- **Shopping Lists** — create lists, add items by name (fuzzy match), mark as purchased
- **Item Library** — 130+ pre-seeded items with emoji icons, categories, and translations (DA/IT/BG)
- **Expiration Calendar** — monthly calendar view showing items by expiration date, color-coded by urgency
- **Image Uploads** — attach photos to library items
- **Repurchase Reminders** — set recurring reminders for items you buy regularly
- **Supermarket Presets** — sort your list by aisle order for different stores
- **API Key Auth** — separate admin and user keys
- **Duplicate Prevention** — adding an existing item returns an error or resets purchased items

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

The compose uses `docker.io/rikcodes/huggy:latest`. The image is built and pushed by GitHub Actions on every push to `main` (requires repo secrets `DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN`).

**Install:** Apps → Install a customized app → paste `docker-compose.yml` (or use its raw URL). Data is stored in `/DATA/AppData/huggy/data`.

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

## Tech Stack

- **Backend:** Python, FastAPI, SQLAlchemy, Uvicorn
- **Database:** SQLite (default) or PostgreSQL
- **Frontend:** Single-page admin panel (vanilla JS)
