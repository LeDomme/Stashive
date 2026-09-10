"""FastAPI application factory and lifecycle."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.admin_users import router as admin_users_router
from app.api.auth import router as auth_router
from app.api.collections import router as collections_router
from app.api.health import router as health_router
from app.api.inventory import router as inventory_router
from app.api.locations import router as locations_router
from app.auth.service import AuthenticationService
from app.config import get_settings
from app.db.database import Database


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Initialize and dispose infrastructure owned by the application."""
    settings = get_settings()
    app.state.database = Database(settings.database_url, settings.sqlite_busy_timeout_ms)
    try:
        with app.state.database.session_factory() as session:
            AuthenticationService(settings).ensure_setup_token(session)
        yield
    finally:
        app.state.database.dispose()


app = FastAPI(title="Stashive API", version="0.1.0", lifespan=lifespan)
app.include_router(health_router, prefix="/api")
app.include_router(auth_router, prefix="/api")
app.include_router(admin_users_router, prefix="/api")
app.include_router(collections_router, prefix="/api")
app.include_router(locations_router, prefix="/api")
app.include_router(inventory_router, prefix="/api")
