import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from sqlalchemy import text
from app.database import engine, SessionLocal, Base
from app.config import settings
from app.seed import seed_database
from app.routers import categories, library, lists, supermarkets, reminders, users, auth
from app.ws import ConnectionManager

ws_manager = ConnectionManager()


def _run_migrations():
    """Add new columns to existing DBs (created_by_id on lists and library_items, user password fields)."""
    with engine.connect() as conn:
        if engine.url.drivername == "sqlite":
            # created_by_id columns
            for table, col, col_def in [
                ("grocery_lists", "created_by_id", "INTEGER"),
                ("library_items", "created_by_id", "INTEGER"),
            ]:
                r = conn.execute(text(f"PRAGMA table_info({table})"))
                if not any(row[1] == col for row in r):
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}"))
                    conn.commit()
            # user auth columns
            for col, col_def in [
                ("password_hash", "TEXT"),
                ("is_active", "INTEGER NOT NULL DEFAULT 1"),
            ]:
                r = conn.execute(text("PRAGMA table_info(users)"))
                if not any(row[1] == col for row in r):
                    conn.execute(text(f"ALTER TABLE users ADD COLUMN {col} {col_def}"))
                    conn.commit()
            # list item actor display names (for OpenClaw / API caller identification)
            for col in ["added_by_display_name", "purchased_by_display_name"]:
                r = conn.execute(text("PRAGMA table_info(grocery_list_items)"))
                if not any(row[1] == col for row in r):
                    conn.execute(text(f"ALTER TABLE grocery_list_items ADD COLUMN {col} VARCHAR(100)"))
                    conn.commit()
        # activity_log table (create if not exists via create_all in lifespan)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    _run_migrations()
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    ws_manager.set_loop(asyncio.get_running_loop())
    app.state.ws_manager = ws_manager
    broadcaster = asyncio.create_task(ws_manager.broadcaster_task())
    yield
    broadcaster.cancel()
    try:
        await broadcaster
    except asyncio.CancelledError:
        pass


app = FastAPI(title=settings.app_title, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(library.router)
app.include_router(lists.router)
app.include_router(supermarkets.router)
app.include_router(reminders.router)
app.include_router(users.router)
app.include_router(auth.router)

static_dir = Path(__file__).parent / "static"
uploads_dir = Path(settings.upload_dir) if settings.upload_dir else Path(__file__).resolve().parent.parent / "uploads"
uploads_dir.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")
app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/")
def root():
    return FileResponse(static_dir / "admin.html")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.websocket("/api/ws")
async def websocket_list_updates(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        ws_manager.disconnect(websocket)
