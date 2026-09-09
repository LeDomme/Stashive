"""FastAPI application factory and lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.health import router as health_router
from app.config import get_settings
from app.db.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and dispose infrastructure owned by the application."""
    settings = get_settings()
    app.state.database = Database(settings.database_url, settings.sqlite_busy_timeout_ms)
    try:
        yield
    finally:
        app.state.database.dispose()


app = FastAPI(title="Stashive API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api")
