"""Tests for SQLite connection requirements."""

from pathlib import Path

from app.db.database import Database


def test_sqlite_connections_enable_required_pragmas(tmp_path: Path) -> None:
    database = Database(f"sqlite:///{tmp_path / 'stashive.db'}", sqlite_busy_timeout_ms=2_500)
    try:
        with database.engine.connect() as connection:
            foreign_keys = connection.exec_driver_sql("PRAGMA foreign_keys").scalar_one()
            busy_timeout = connection.exec_driver_sql("PRAGMA busy_timeout").scalar_one()
            journal_mode = connection.exec_driver_sql("PRAGMA journal_mode").scalar_one()

        assert foreign_keys == 1
        assert busy_timeout == 2_500
        assert journal_mode == "wal"
    finally:
        database.dispose()
