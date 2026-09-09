"""Local account, bootstrap-token, and opaque-session operations."""

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerifyMismatchError
from sqlalchemy import Select, func, select, update
from sqlalchemy.orm import Session as DatabaseSession

from app.config import Settings
from app.db.models import Session, SetupToken, User

logger = logging.getLogger(__name__)
password_hasher = PasswordHasher()


class AuthenticationError(Exception):
    """Raised when supplied authentication credentials are not valid."""


class SetupUnavailableError(Exception):
    """Raised when an instance already has an account."""


def utc_now() -> datetime:
    """Return the current timezone-aware UTC time."""
    return datetime.now(UTC)


def normalize_username(username: str) -> str:
    """Normalize usernames as trimmed, case-insensitive local identities."""
    return username.strip().casefold()


def hash_secret(value: str) -> str:
    """Return a stable one-way hash for high-entropy opaque tokens."""
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class AuthenticationService:
    """Perform local authentication operations within explicit transactions."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def setup_required(self, session: DatabaseSession) -> bool:
        """Return whether the first local account still needs to be created."""
        return session.scalar(select(func.count()).select_from(User)) == 0

    def ensure_setup_token(self, session: DatabaseSession) -> None:
        """Create and log a bootstrap token only for an uninitialized instance."""
        if not self.setup_required(session):
            return

        now = utc_now()
        valid_token = session.scalar(
            select(SetupToken.id).where(
                SetupToken.consumed_at.is_(None),
                SetupToken.expires_at > now,
            )
        )
        if valid_token is not None:
            return

        test_token = self._configured_test_token()
        token = test_token or secrets.token_urlsafe(32)
        session.add(
            SetupToken(
                token_hash=hash_secret(token),
                expires_at=now + timedelta(minutes=self.settings.auth_setup_token_lifetime_minutes),
            )
        )
        session.commit()
        logger.info("Stashive first-run setup token: %s", token)

    def complete_setup(
        self,
        session: DatabaseSession,
        *,
        token: str,
        username: str,
        display_name: str | None,
        password: str,
    ) -> tuple[User, str, str]:
        """Create the initial administrator and an authenticated browser session."""
        if not self.setup_required(session):
            raise SetupUnavailableError

        now = utc_now()
        token_hash = hash_secret(token)
        setup_token = session.scalar(
            select(SetupToken).where(
                SetupToken.token_hash == token_hash,
                SetupToken.consumed_at.is_(None),
                SetupToken.expires_at > now,
            )
        )
        if setup_token is None or not hmac.compare_digest(setup_token.token_hash, token_hash):
            raise AuthenticationError

        user = User(
            username=normalize_username(username),
            display_name=display_name.strip() if display_name else None,
            password_hash=password_hasher.hash(password),
            is_instance_admin=True,
        )
        session.add(user)
        session.flush()
        session.execute(
            update(SetupToken)
            .where(SetupToken.consumed_at.is_(None))
            .values(consumed_at=now)
        )
        raw_token, raw_csrf_token = self._create_session(session, user, now)
        session.commit()
        return user, raw_token, raw_csrf_token

    def login(
        self,
        session: DatabaseSession,
        *,
        username: str,
        password: str,
    ) -> tuple[User, str, str]:
        """Verify local credentials and create an opaque browser session."""
        user = session.scalar(select(User).where(User.username == normalize_username(username)))
        if user is None or not user.is_active:
            raise AuthenticationError
        try:
            password_hasher.verify(user.password_hash, password)
        except (InvalidHashError, VerifyMismatchError) as error:
            raise AuthenticationError from error

        raw_token, raw_csrf_token = self._create_session(session, user, utc_now())
        session.commit()
        return user, raw_token, raw_csrf_token

    def get_current_user(self, session: DatabaseSession, raw_token: str | None) -> User | None:
        """Return the active user represented by an unexpired opaque session token."""
        if not raw_token:
            return None
        now = utc_now()
        token_hash = hash_secret(raw_token)
        browser_session = session.scalar(
            self._active_session_query(token_hash, now)
        )
        return browser_session.user if browser_session and browser_session.user.is_active else None

    def logout(
        self,
        session: DatabaseSession,
        *,
        raw_token: str | None,
        csrf_token: str | None,
    ) -> None:
        """Revoke the current session after validating its CSRF token."""
        browser_session = self._active_session(session, raw_token)
        if browser_session is None or not self._valid_csrf(browser_session, csrf_token):
            raise AuthenticationError
        browser_session.revoked_at = utc_now()
        session.commit()

    def _create_session(
        self,
        session: DatabaseSession,
        user: User,
        now: datetime,
    ) -> tuple[str, str]:
        raw_token = secrets.token_urlsafe(32)
        raw_csrf_token = secrets.token_urlsafe(32)
        session.add(
            Session(
                user=user,
                token_hash=hash_secret(raw_token),
                csrf_token_hash=hash_secret(raw_csrf_token),
                expires_at=now + timedelta(hours=self.settings.auth_session_lifetime_hours),
            )
        )
        return raw_token, raw_csrf_token

    def _active_session(
        self,
        session: DatabaseSession,
        raw_token: str | None,
    ) -> Session | None:
        if not raw_token:
            return None
        return session.scalar(self._active_session_query(hash_secret(raw_token), utc_now()))

    def _active_session_query(self, token_hash: str, now: datetime) -> Select[tuple[Session]]:
        return (
            select(Session)
            .where(
                Session.token_hash == token_hash,
                Session.expires_at > now,
                Session.revoked_at.is_(None),
            )
        )

    def _valid_csrf(self, browser_session: Session, csrf_token: str | None) -> bool:
        return csrf_token is not None and hmac.compare_digest(
            browser_session.csrf_token_hash,
            hash_secret(csrf_token),
        )

    def _configured_test_token(self) -> str | None:
        token = self.settings.auth_test_setup_token
        if token is None:
            return None
        if self.settings.app_environment != "test":
            raise RuntimeError("AUTH_TEST_SETUP_TOKEN is only permitted when APP_ENVIRONMENT=test")
        return token.get_secret_value()
