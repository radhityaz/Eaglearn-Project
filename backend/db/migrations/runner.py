from __future__ import annotations

from datetime import datetime
from typing import Callable, List, Tuple

from sqlalchemy import Column, DateTime, MetaData, String, Table, select
from sqlalchemy.engine import Engine

from . import migration_001_add_core_tables

Migration = Tuple[str, Callable[[Engine], None]]


MIGRATIONS: List[Migration] = [
    ("001_add_core_tables", migration_001_add_core_tables.upgrade),
]


def apply_migrations(engine: Engine) -> None:
    """
    Apply pending migrations in order.

    This lightweight runner keeps track of executed migrations in a schema_migrations
    table so that repeated application is safe.
    """
    metadata = MetaData()
    migrations_table = Table(
        "schema_migrations",
        metadata,
        Column("name", String(255), primary_key=True),
        Column("applied_at", DateTime, nullable=False),
    )
    metadata.create_all(engine)

    with engine.begin() as connection:
        applied = {
            row[0] for row in connection.execute(select(migrations_table.c.name))
        }
        for name, upgrade in MIGRATIONS:
            if name in applied:
                continue
            upgrade(engine)
            connection.execute(
                migrations_table.insert().values(
                    name=name, applied_at=datetime.utcnow()
                )
            )
