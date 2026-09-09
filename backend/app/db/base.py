"""SQLAlchemy declarative base for future persistent models."""

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base class for Stashive SQLAlchemy models."""
