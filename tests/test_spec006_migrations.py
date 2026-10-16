"""SPEC-006A database migrations: new SQLite, populated baseline and fail-closed."""
import sqlite3

import pytest
from sqlalchemy import create_engine, inspect

from handoff_hub.poc_db import Base, Operation, make_session_factory

BASELINE = (
    "operations", "integrations", "queues", "operators",
    "queue_memberships", "handoff_sessions", "session_events",
    "messages", "outbox_events", "handoff_offers", "session_transfers",
    "auth_users", "auth_sessions", "login_throttles",
    "demo_seed_revisions", "dispatch_turns",
)


def test_empty_database_receives_versioned_schema(tmp_path):
    database = tmp_path / "new.db"
    factory, engine = make_session_factory(f"sqlite:///{database}")
    try:
        tables = set(inspect(engine).get_table_names())
        assert "queue_role_grants" in tables
        assert "alembic_version" in tables
        with factory() as db:
            revision = db.connection().exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one()
            assert revision == "0002_queue_grants"
    finally:
        engine.dispose()


def test_populated_poc_baseline_upgrades_and_preserves_data_and_backup(tmp_path):
    database = tmp_path / "previous.db"
    url = f"sqlite:///{database}"
    old_engine = create_engine(url, future=True)
    try:
        Base.metadata.create_all(
            old_engine,
            tables=[Base.metadata.tables[name] for name in BASELINE],
        )
        with old_engine.begin() as conn:
            conn.execute(Operation.__table__.insert().values(
                id="demo", name="Preserved demonstration",
            ))
    finally:
        old_engine.dispose()

    _, engine = make_session_factory(url)
    try:
        assert "queue_role_grants" in inspect(engine).get_table_names()
        with engine.connect() as conn:
            assert conn.exec_driver_sql(
                "SELECT name FROM operations WHERE id='demo'"
            ).scalar_one() == "Preserved demonstration"
            assert conn.exec_driver_sql(
                "SELECT version_num FROM alembic_version"
            ).scalar_one() == "0002_queue_grants"
    finally:
        engine.dispose()

    backups = list(tmp_path.glob("previous.db.before-spec006-*.bak"))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as old:
        assert old.execute(
            "SELECT name FROM operations WHERE id='demo'"
        ).fetchone()[0] == "Preserved demonstration"
        assert "queue_role_grants" not in {
            row[0] for row in old.execute("SELECT name FROM sqlite_master")
        }

    # Restart cannot stamp, copy or erase records a second time.
    _, engine = make_session_factory(url)
    engine.dispose()
    assert len(list(tmp_path.glob("previous.db.before-spec006-*.bak"))) == 1


def test_partial_schema_refuses_unsafe_migration(tmp_path):
    database = tmp_path / "partial.db"
    url = f"sqlite:///{database}"
    engine = create_engine(url, future=True)
    try:
        Operation.__table__.create(engine)
        with engine.begin() as conn:
            conn.execute(Operation.__table__.insert().values(
                id="demo", name="Do not erase",
            ))
    finally:
        engine.dispose()

    with pytest.raises(RuntimeError, match="Esquema SQLite antigo/parcial"):
        make_session_factory(url)
    with sqlite3.connect(database) as conn:
        assert conn.execute("SELECT name FROM operations").fetchone()[0] == "Do not erase"
        assert "alembic_version" not in {
            row[0] for row in conn.execute("SELECT name FROM sqlite_master")
        }
