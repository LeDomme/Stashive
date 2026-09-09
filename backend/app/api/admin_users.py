"""Instance-administrator endpoints for local user accounts."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DatabaseSession

from app.api.auth import current_user_or_401, get_session
from app.db.models import User
from app.users.schemas import (
    AdminUserCreateInput,
    AdminUserResponse,
    AdminUserUpdateInput,
    PasswordResetInput,
)
from app.users.service import (
    DuplicateUsernameError,
    LastActiveInstanceAdminError,
    UserManagementService,
)

router = APIRouter(prefix="/admin/users", tags=["admin-users"])


def instance_admin_or_403(user: User = Depends(current_user_or_401)) -> User:
    """Require instance administration without granting collection access."""
    if not user.is_instance_admin:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Instance admin required")
    return user


def user_or_404(session: DatabaseSession, user_id: int) -> User:
    """Resolve a local account for an already-authorized administrator."""
    user = session.get(User, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return user


def management_error_to_http(error: Exception) -> HTTPException:
    """Translate safe domain errors to stable admin API responses."""
    if isinstance(error, DuplicateUsernameError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Username is already in use"
        )
    if isinstance(error, LastActiveInstanceAdminError):
        return HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="At least one active instance admin is required",
        )
    raise error


@router.get("", response_model=list[AdminUserResponse])
def list_users(
    session: DatabaseSession = Depends(get_session),
    _: User = Depends(instance_admin_or_403),
) -> list[User]:
    """List safe local account details for an instance administrator."""
    return UserManagementService().list_users(session)


@router.post("", response_model=AdminUserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: AdminUserCreateInput,
    session: DatabaseSession = Depends(get_session),
    _: User = Depends(instance_admin_or_403),
) -> User:
    """Create a local account after bootstrap has completed."""
    try:
        return UserManagementService().create_user(session, **payload.model_dump())
    except DuplicateUsernameError as error:
        raise management_error_to_http(error) from error


@router.patch("/{user_id}", response_model=AdminUserResponse)
def update_user(
    user_id: int,
    payload: AdminUserUpdateInput,
    session: DatabaseSession = Depends(get_session),
    _: User = Depends(instance_admin_or_403),
) -> User:
    """Update mutable account fields without supporting username renames."""
    user = user_or_404(session, user_id)
    changes = payload.model_dump(exclude_unset=True)
    try:
        return UserManagementService().update_user(
            session,
            user,
            display_name=payload.display_name,
            update_display_name="display_name" in changes,
            is_instance_admin=changes.get("is_instance_admin"),
            is_active=changes.get("is_active"),
        )
    except LastActiveInstanceAdminError as error:
        raise management_error_to_http(error) from error


@router.post("/{user_id}/password", response_model=AdminUserResponse)
def reset_password(
    user_id: int,
    payload: PasswordResetInput,
    session: DatabaseSession = Depends(get_session),
    _: User = Depends(instance_admin_or_403),
) -> User:
    """Reset a local password and invalidate all sessions for that account."""
    return UserManagementService().reset_password(
        session, user_or_404(session, user_id), **payload.model_dump()
    )
