"""Cookie-based local authentication endpoints."""

from collections import defaultdict, deque
from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session as DatabaseSession

from app.auth.schemas import AuthStatusResponse, CurrentUserResponse, LoginRequest, SetupRequest
from app.auth.service import AuthenticationError, AuthenticationService, SetupUnavailableError
from app.config import get_settings
from app.db.database import Database
from app.db.models import User

router = APIRouter(prefix="/auth", tags=["auth"])

_setup_attempts: dict[str, deque[datetime]] = defaultdict(deque)
_setup_attempt_window = timedelta(minutes=10)
_setup_attempt_limit = 5


def get_database(request: Request) -> Database:
    """Return the application database."""
    return request.app.state.database


def get_session(database: Database = Depends(get_database)):
    """Yield a request-scoped SQLAlchemy session."""
    yield from database.session()


def get_auth_service() -> AuthenticationService:
    """Build the authentication service from immutable settings."""
    return AuthenticationService(get_settings())


def current_user_or_401(
    request: Request,
    session: DatabaseSession = Depends(get_session),
    service: AuthenticationService = Depends(get_auth_service),
) -> User:
    """Resolve the active user from the opaque session cookie."""
    raw_token = request.cookies.get(get_settings().auth_session_cookie_name)
    user = service.get_current_user(session, raw_token)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return user


def _set_auth_cookies(response: Response, raw_token: str, raw_csrf_token: str) -> None:
    settings = get_settings()
    common = {
        "secure": settings.auth_cookie_secure,
        "samesite": "lax",
        "path": "/",
        "max_age": settings.auth_session_lifetime_hours * 60 * 60,
    }
    response.set_cookie(
        settings.auth_session_cookie_name,
        raw_token,
        httponly=True,
        **common,
    )
    response.set_cookie(
        settings.auth_csrf_cookie_name,
        raw_csrf_token,
        httponly=False,
        **common,
    )


def _clear_auth_cookies(response: Response) -> None:
    settings = get_settings()
    response.delete_cookie(settings.auth_session_cookie_name, path="/")
    response.delete_cookie(settings.auth_csrf_cookie_name, path="/")


def _enforce_setup_rate_limit(request: Request) -> None:
    now = datetime.now(UTC)
    client_address = request.client.host if request.client else "unknown"
    attempts = _setup_attempts[client_address]
    while attempts and now - attempts[0] > _setup_attempt_window:
        attempts.popleft()
    if len(attempts) >= _setup_attempt_limit:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Try again later")
    attempts.append(now)


@router.get("/status", response_model=AuthStatusResponse)
def auth_status(
    request: Request,
    session: DatabaseSession = Depends(get_session),
    service: AuthenticationService = Depends(get_auth_service),
) -> AuthStatusResponse:
    """Report whether setup is required and whether this browser is authenticated."""
    raw_token = request.cookies.get(get_settings().auth_session_cookie_name)
    return AuthStatusResponse(
        setup_required=service.setup_required(session),
        authenticated=service.get_current_user(session, raw_token) is not None,
    )


@router.post("/setup", response_model=CurrentUserResponse, status_code=status.HTTP_201_CREATED)
def setup(
    payload: SetupRequest,
    request: Request,
    response: Response,
    session: DatabaseSession = Depends(get_session),
    service: AuthenticationService = Depends(get_auth_service),
) -> CurrentUserResponse:
    """Create the first instance administrator with a one-time setup token."""
    _enforce_setup_rate_limit(request)
    try:
        user, raw_token, raw_csrf_token = service.complete_setup(
            session,
            token=payload.token,
            username=payload.username,
            display_name=payload.display_name,
            password=payload.password,
        )
    except SetupUnavailableError as error:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Setup unavailable",
        ) from error
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid setup credentials",
        ) from error
    _set_auth_cookies(response, raw_token, raw_csrf_token)
    return CurrentUserResponse.model_validate(user, from_attributes=True)


@router.post("/login", response_model=CurrentUserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: DatabaseSession = Depends(get_session),
    service: AuthenticationService = Depends(get_auth_service),
) -> CurrentUserResponse:
    """Create a browser session from local account credentials."""
    try:
        user, raw_token, raw_csrf_token = service.login(
            session,
            username=payload.username,
            password=payload.password,
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
        ) from error
    _set_auth_cookies(response, raw_token, raw_csrf_token)
    return CurrentUserResponse.model_validate(user, from_attributes=True)


@router.get("/me", response_model=CurrentUserResponse)
def me(user: User = Depends(current_user_or_401)) -> CurrentUserResponse:
    """Return the current authenticated user without password data."""
    return CurrentUserResponse.model_validate(user, from_attributes=True)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(
    request: Request,
    response: Response,
    session: DatabaseSession = Depends(get_session),
    service: AuthenticationService = Depends(get_auth_service),
) -> Response:
    """Revoke the current session and clear browser cookies."""
    try:
        service.logout(
            session,
            raw_token=request.cookies.get(get_settings().auth_session_cookie_name),
            csrf_token=request.headers.get("X-CSRF-Token"),
        )
    except AuthenticationError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
        ) from error
    _clear_auth_cookies(response)
    response.status_code = status.HTTP_204_NO_CONTENT
    return response
