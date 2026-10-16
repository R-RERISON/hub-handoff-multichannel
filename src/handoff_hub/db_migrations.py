"""Safe local SQLite migration bootstrap. Never reset or overwrite POC data."""
from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect

ROOT = Path(__file__).resolve().parents[2]
REQUIRED_BASELINE = frozenset((
    "operations", "integrations", "queues", "operators",
    "queue_memberships", "handoff_sessions", "session_events",
    "messages", "outbox_events", "handoff_offers", "session_transfers",
    "auth_users", "auth_sessions", "login_throttles",
    "demo_seed_revisions", "dispatch_turns",
))


def upgrade_database(database_url: str) -> str | None:
    """Upgrade an empty/new or complete existing 0.5 SQLite DB.

    Existing databases are backed up via sqlite3.backup before *any* stamping
    or DDL. An unknown/partial schema fails closed; do not guess a version.
    The returned backup path can be used for a controlled manual rollback.
    """
    if not database_url.startswith("sqlite:///"):
        raise RuntimeError("SPEC-006 migrations currently support only file-based SQLite")
    if database_url.endswith(":memory:"):
        raise RuntimeError("Use in-memory test schema setup, not file migration")
    config = Config(str(ROOT / "alembic.ini"))
    config.set_main_option("sqlalchemy.url", database_url.replace("%", "%%"))
    scripts = ScriptDirectory.from_config(config)
    desired = scripts.get_current_head()
    engine = create_engine(database_url, future=True)
    try:
        with engine.connect() as conn:
            existing = set(inspect(conn).get_table_names())
            current = MigrationContext.configure(conn).get_current_revision()
    finally:
        engine.dispose()

    if current == desired:
        return None
    if existing and not REQUIRED_BASELINE.issubset(existing):
        missing = sorted(REQUIRED_BASELINE - existing)
        raise RuntimeError(
            "Esquema SQLite antigo/parcial: upgrade bloqueado, tabelas faltando: "
            + ", ".join(missing)
        )
    if current is None and "queue_role_grants" in existing:
        raise RuntimeError("Concessões existentes sem versão Alembic; exigir revisão manual")

    backup_path = None
    file_path = Path(database_url.removeprefix("sqlite:///")).resolve()
    if existing and file_path.exists():
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        destination = file_path.with_name(f"{file_path.name}.before-spec006-{stamp}.bak")
        # SQLite backup safely includes committed WAL pages and is consistent.
        with sqlite3.connect(str(file_path)) as source:
            with sqlite3.connect(str(destination)) as backup:
                source.backup(backup)
        backup_path = str(destination)
        print(f"[Handoff] Backup SQLite antes do upgrade: {backup_path}", flush=True)

    if current is None and existing:
        # Recognize complete POC-005 schema; do not recreate its tables.
        command.stamp(config, "0001_poc_baseline")
    command.upgrade(config, "head")
    return backup_path
