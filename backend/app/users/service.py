"""Instance-level local account management operations."""

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session as DatabaseSession

from app.auth.service import normalize_username, password_hasher, utc_now
from app.db.models import Session, User


class DuplicateUsernameError(Exception):
    """Raised when a normalized local username already exists."""


class LastActiveInstanceAdminError(Exception):
    """Raised when an operation would remove the final active instance administrator."""


class UserManagementService:
    """Manage local accounts while preserving instance-administration invariants."""

    def list_users(self, session: DatabaseSession) -> list[User]:
        """Return all local accounts in stable identifier order."""
        return list(session.scalars(select(User).order_by(User.id)))

    def create_user(
        self,
        session: DatabaseSession,
        *,
        username: str,
        display_name: str | None,
        password: str,
        is_instance_admin: bool,
    ) -> User:
        """Create a normalized local account with an Argon2 password hash."""
        normalized_username = normalize_username(username)
        if session.scalar(select(User.id).where(User.username == normalized_username)) is not None:
            raise DuplicateUsernameError
        user = User(
            username=normalized_username,
            display_name=display_name.strip() if display_name else None,
            password_hash=password_hasher.hash(password),
            is_instance_admin=is_instance_admin,
        )
        session.add(user)
        session.commit()
        session.refresh(user)
        return user

    def update_user(
        self,
        session: DatabaseSession,
        user: User,
        *,
        display_name: str | None,
        update_display_name: bool,
        is_instance_admin: bool | None = None,
        is_active: bool | None = None,
    ) -> User:
        """Update mutable account fields and revoke sessions on deactivation."""
        next_is_instance_admin = (
            user.is_instance_admin if is_instance_admin is None else is_instance_admin
        )
        next_is_active = user.is_active if is_active is None else is_active
        self._ensure_active_admin_remains(session, user, next_is_instance_admin, next_is_active)

        if update_display_name:
            user.display_name = (
                display_name.strip() if isinstance(display_name, str) and display_name else None
            )
        if is_instance_admin is not None:
            user.is_instance_admin = is_instance_admin
        if is_active is not None:
            user.is_active = is_active
            if not is_active:
                self._revoke_sessions(session, user.id)
        session.commit()
        session.refresh(user)
        return user

    def reset_password(self, session: DatabaseSession, user: User, *, password: str) -> User:
        """Set a new Argon2 password hash and revoke every active browser session."""
        user.password_hash = password_hasher.hash(password)
        self._revoke_sessions(session, user.id)
        session.commit()
        session.refresh(user)
        return user

    def _ensure_active_admin_remains(
        self,
        session: DatabaseSession,
        user: User,
        next_is_instance_admin: bool,
        next_is_active: bool,
    ) -> None:
        if not user.is_instance_admin or not user.is_active:
            return
        if next_is_instance_admin and next_is_active:
            return
        active_admin_count = session.scalar(
            select(func.count()).select_from(User).where(User.is_instance_admin, User.is_active)
        )
        if active_admin_count == 1:
            raise LastActiveInstanceAdminError

    def _revoke_sessions(self, session: DatabaseSession, user_id: int) -> None:
        session.execute(
            update(Session)
            .where(Session.user_id == user_id, Session.revoked_at.is_(None))
            .values(revoked_at=utc_now())
        )
