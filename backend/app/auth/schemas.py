"""Authentication request and response schemas."""

from pydantic import BaseModel, Field


class SetupRequest(BaseModel):
    """Credentials and token used to create the first administrator."""

    token: str = Field(min_length=1, max_length=512)
    username: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=12, max_length=256)


class LoginRequest(BaseModel):
    """Credentials used to create a browser session."""

    username: str = Field(min_length=1, max_length=255)
    password: str = Field(min_length=1, max_length=256)


class CurrentUserResponse(BaseModel):
    """Public account data for the authenticated browser user."""

    id: int
    username: str
    display_name: str | None
    is_instance_admin: bool


class AuthStatusResponse(BaseModel):
    """Authentication state required for the initial client route."""

    setup_required: bool
    authenticated: bool
