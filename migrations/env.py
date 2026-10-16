"""Alembic online configuration; schema changes are explicit, never auto-applied."""
from alembic import context
from sqlalchemy import create_engine, pool

from handoff_hub.poc_db import Base

target_metadata = Base.metadata


def run_migrations_online() -> None:
    config = context.config
    url = config.get_main_option("sqlalchemy.url")
    if not url or not url.startswith("sqlite:"):
        raise RuntimeError("SPEC-006B-1 baseline supports SQLite only")
    engine = create_engine(url, poolclass=pool.NullPool)
    try:
        with engine.connect() as connection:
            context.configure(connection=connection, target_metadata=target_metadata)
            with context.begin_transaction():
                context.run_migrations()
    finally:
        engine.dispose()


if context.is_offline_mode():
    raise RuntimeError("Offline SQL generation is unavailable for this SQLite baseline")
run_migrations_online()
