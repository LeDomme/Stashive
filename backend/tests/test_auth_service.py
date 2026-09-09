"""Tests for local account, setup-token, and opaque-session operations."""

from datetime import timedelta

import pytest
from argon2 import PasswordHasher
from pydantic import SecretStr
from sqlalchemy import select

from app.auth.service import (
    AuthenticationError,
    AuthenticationService,
    SetupUnavailableError,
    hash_secret,
    normalize_username,
    utc_now,
)
from app.config import Settings
from app.db.database import Database
from app.db.models import Session, SetupToken, User

password_hasher = PasswordHasher()


def auth_settings() -> Settings:
    """Return deterministic test-only authentication settings."""
    return Settings(
        app_environment="test",
        auth_test_setup_token=SecretStr("test-setup-token"),
        auth_session_lifetime_hours=1,
    )


def test_username_normalization_is_trimmed_and_casefolded() -> None:
    assert normalize_username("  ALIce  ") == "alice"


def test_setup_creates_admin_consumes_tokens_and_never_stores_plaintext(database: Database) -> None:
    service = AuthenticationService(auth_settings())
    with database.session_factory() as session:
        service.ensure_setup_token(session)
        stored_token = session.scalar(select(SetupToken))
        assert stored_token is not None
        assert stored_token.token_hash == hash_secret("test-setup-token")
        assert stored_token.token_hash != "test-setup-token"

        user, raw_session_token, raw_csrf_token = service.complete_setup(
            session,
            token="test-setup-token",
            username="  ADMIN  ",
            display_name=" Administrator ",
            password="correct horse battery staple",
        )

        assert user.username == "admin"
        assert user.display_name == "Administrator"
        assert user.is_instance_admin is True
        assert service.setup_required(session) is False
        assert session.scalar(select(SetupToken.consumed_at)) is not None
        stored_session = session.scalar(select(Session))
        assert stored_session is not None
        assert stored_session.token_hash != raw_session_token
        assert stored_session.csrf_token_hash != raw_csrf_token
        assert service.get_current_user(session, raw_session_token) == user

        with pytest.raises(SetupUnavailableError):
            service.complete_setup(
                session,
                token="test-setup-token",
                username="second",
                display_name=None,
                password="correct horse battery staple",
            )


def test_login_logout_and_csrf_validation(database: Database) -> None:
    service = AuthenticationService(auth_settings())
    with database.session_factory() as session:
        user = User(
            username="alice",
            password_hash=password_hasher.hash("correct horse battery staple"),
        )
        session.add(user)
        session.commit()

        logged_in, raw_token, raw_csrf_token = service.login(
            session,
            username=" ALICE ",
            password="correct horse battery staple",
        )
        assert logged_in.id == user.id

        with pytest.raises(AuthenticationError):
            service.logout(session, raw_token=raw_token, csrf_token="wrong")

        service.logout(session, raw_token=raw_token, csrf_token=raw_csrf_token)
        assert service.get_current_user(session, raw_token) is None


def test_expired_sessions_are_not_authenticated(database: Database) -> None:
    service = AuthenticationService(auth_settings())
    with database.session_factory() as session:
        user = User(
            username="alice",
            password_hash=password_hasher.hash("correct horse battery staple"),
        )
        session.add(user)
        session.flush()
        session.add(
            Session(
                user_id=user.id,
                token_hash=hash_secret("expired-session"),
                csrf_token_hash=hash_secret("csrf"),
                expires_at=utc_now() - timedelta(seconds=1),
            )
        )
        session.commit()

        assert service.get_current_user(session, "expired-session") is None
