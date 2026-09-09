"""Tests for the repository-foundation health endpoint."""

from app.api.health import health


def test_health_reports_ok() -> None:
    assert health().model_dump() == {"status": "ok"}
