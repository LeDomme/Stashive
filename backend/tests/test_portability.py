"""Tests preventing database-vendor-specific model types from entering the core."""

from sqlalchemy import Date, DateTime, Integer, String, Text
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from app.db.models import CatalogEntry, Collection, Edition, Identifier, InventoryItem


def test_database_core_uses_only_portable_sqlalchemy_column_types() -> None:
    allowed_types = (Date, DateTime, Integer, String, Text)
    tables = (
        Collection.__table__,
        CatalogEntry.__table__,
        Edition.__table__,
        Identifier.__table__,
        InventoryItem.__table__,
    )

    for table in tables:
        for column in table.columns:
            assert isinstance(column.type, allowed_types)

        ddl = str(CreateTable(table).compile(dialect=postgresql.dialect())).upper()
        assert " JSONB" not in ddl
        assert " ENUM" not in ddl
