from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path

from app.database import engine, SessionLocal, Base
from app.config import settings
from app.seed import seed_database
from app.routers import categories, library, lists, supermarkets, reminders, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    if settings.seed_on_startup:
        db = SessionLocal()
        try:
            seed_database(db)
        finally:
            db.close()
    yield


app = FastAPI(title=settings.app_title, lifespan=lifespan)

app.include_router(categories.router)
app.include_router(library.router)
app.include_router(lists.router)
app.include_router(supermarkets.router)
app.include_router(reminders.router)
app.include_router(users.router)

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
