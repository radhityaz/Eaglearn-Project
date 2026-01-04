"""Initial migration to ensure core tables and indexes exist."""

from sqlalchemy.engine import Engine

from backend.db.models import Base


def upgrade(engine: Engine) -> None:
    """Create tables defined in SQLAlchemy metadata."""
    Base.metadata.create_all(bind=engine)
