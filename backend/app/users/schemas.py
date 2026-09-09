"""Transport schemas for instance administrator user management."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, field_validator


class AdminUserResponse(BaseModel):
    """Safe local account data visible to instance administrators."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    display_name: str | None
    is_instance_admin: bool
    is_active: bool
    created_at: datetime


class AdminUserCreateInput(BaseModel):
    """Fields accepted when an instance administrator creates a local account."""

    username: str = Field(min_length=1, max_length=255)
    display_name: str | None = Field(default=None, max_length=255)
    password: str = Field(min_length=12, max_length=256)
    is_instance_admin: bool = False

    @field_validator("username")
    @classmethod
    def username_must_not_be_blank(cls, value: str) -> str:
        """Reject whitespace-only local identities before persistence."""
        if not value.strip():
            raise ValueError("Username must not be blank")
        return value


class AdminUserUpdateInput(BaseModel):
    """Mutable, non-secret local account fields."""

    display_name: str | None = Field(default=None, max_length=255)
    is_instance_admin: bool | None = None
    is_active: bool | None = None


class PasswordResetInput(BaseModel):
    """Password supplied by an instance administrator for a local account."""

    password: str = Field(min_length=12, max_length=256)
