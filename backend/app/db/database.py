"""Portable SQLAlchemy database setup."""

from collections.abc import Generator
from pathlib import Path

from sqlalchemy import Engine, create_engine, event, text
from sqlalchemy.engine import URL, make_url
from sqlalchemy.orm import Session, sessionmaker


class Database:
    """Own the SQLAlchemy engine and sessions for one application instance."""

    def __init__(self, database_url: str, sqlite_busy_timeout_ms: int) -> None:
        self.url: URL = make_url(database_url)
        self.sqlite_busy_timeout_ms = sqlite_busy_timeout_ms
        self._prepare_sqlite_directory()
        self.engine: Engine = create_engine(
            self.url,
            connect_args={"check_same_thread": False} if self.is_sqlite else {},
            pool_pre_ping=True,
        )
        if self.is_sqlite:
            event.listen(self.engine, "connect", self._configure_sqlite_connection)
        self.session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    @property
    def is_sqlite(self) -> bool:
        """Whether this database uses SQLite."""
        return self.url.get_backend_name() == "sqlite"

    def _prepare_sqlite_directory(self) -> None:
        if not self.is_sqlite or self.url.database in (None, ":memory:"):
            return
        Path(self.url.database).expanduser().parent.mkdir(parents=True, exist_ok=True)

    def _configure_sqlite_connection(self, dbapi_connection: object, _: object) -> None:
        cursor = dbapi_connection.cursor()  # type: ignore[union-attr]
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.execute(f"PRAGMA busy_timeout={self.sqlite_busy_timeout_ms}")
        if self.url.database not in (None, ":memory:"):
            cursor.execute("PRAGMA journal_mode=WAL")
        cursor.close()

    def session(self) -> Generator[Session, None, None]:
        """Yield a short-lived database session for an API request."""
        session = self.session_factory()
        try:
            yield session
        finally:
            session.close()

    def check_connection(self) -> None:
        """Raise if the configured database cannot answer a simple query."""
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        """Release database connections during application shutdown."""
        self.engine.dispose()
