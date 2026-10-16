"""Alembic environment for the local POC database only."""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from handoff_hub.poc_db import Base

config = context.config
if config.config_file_name and config.get_section("loggers"):
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            compare_type=True, render_as_batch=True,
        )
        with context.begin_transaction():
            context.run_migrations()
    connectable.dispose()


run_migrations_online()
