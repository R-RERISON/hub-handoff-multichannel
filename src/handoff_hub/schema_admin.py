"""Safe, opt-in SQLite baseline adoption for an already populated Handoff Hub POC.

No command here is called by start.cmd. Only the explicit 'adopt' command stamps
an existing schema; it first verifies its structure and makes a SQLite backup.
Run with API and dispatcher stopped. Never use this with corporate data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import quote

from alembic import command
from alembic.config import Config
from sqlalchemy.dialects import sqlite
from sqlalchemy.engine import URL

from handoff_hub.poc_db import Base

BASELINE_REVISION = "006b1_poc_baseline"
PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DB = PROJECT_ROOT / "data" / "handoff-poc.db"
DEFAULT_BACKUPS = PROJECT_ROOT / "data" / "backups"


class SchemaSafetyError(RuntimeError):
    """Refuse to stamp an unknown or incompatible SQLite database."""


def _read_only(path: Path) -> sqlite3.Connection:
    if not path.is_file():
        raise SchemaSafetyError(f"Database does not exist: {path}")
    uri = "file:" + quote(path.resolve().as_posix(), safe="/:") + "?mode=ro"
    return sqlite3.connect(uri, uri=True, timeout=10)


def _pragma(conn: sqlite3.Connection, name: str, table: str) -> list[tuple]:
    # Names are taken only from our own trusted declarative metadata.
    escaped = table.replace('"', '""')
    return conn.execute(f'PRAGMA {name}("{escaped}")').fetchall()


def verify_database(path: Path) -> dict:
    """Read-only, fail-closed validation against the checked-in POC schema."""
    with _read_only(path) as db:
        integrity = db.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            raise SchemaSafetyError("SQLite integrity_check failed")
        actual_tables = {
            row[0] for row in db.execute(
                "SELECT name FROM sqlite_master WHERE type='table' "
                "AND name NOT LIKE 'sqlite_%'"
            )
        }
        existing_version = "alembic_version" in actual_tables
        actual_tables.discard("alembic_version")
        expected_tables = set(Base.metadata.tables)
        if actual_tables != expected_tables:
            missing = sorted(expected_tables - actual_tables)
            unknown = sorted(actual_tables - expected_tables)
            raise SchemaSafetyError(
                f"Unrecognized POC schema; missing tables={missing}; extra tables={unknown}"
            )
        dialect = sqlite.dialect()
        for table in Base.metadata.sorted_tables:
            current = {
                row[1]: row for row in _pragma(db, "table_info", table.name)
            }
            expected_cols = {column.name: column for column in table.columns}
            if set(current) != set(expected_cols):
                raise SchemaSafetyError(f"Column mismatch in {table.name}")
            for name, column in expected_cols.items():
                row = current[name]
                actual_type = row[2].strip().upper()
                expected_type = str(column.type.compile(dialect=dialect)).upper()
                if actual_type != expected_type:
                    raise SchemaSafetyError(
                        f"Type mismatch: {table.name}.{name}: "
                        f"{actual_type} != {expected_type}"
                    )
                if bool(row[5]) != bool(column.primary_key):
                    raise SchemaSafetyError(f"Primary key mismatch: {table.name}.{name}")
                if not column.primary_key and bool(row[3]) == bool(column.nullable):
                    raise SchemaSafetyError(f"Nullability mismatch: {table.name}.{name}")
            required_indexes = {index.name for index in table.indexes}
            found_indexes = {
                index[1] for index in _pragma(db, "index_list", table.name)
                if not index[1].startswith("sqlite_autoindex")
            }
            if required_indexes != found_indexes:
                raise SchemaSafetyError(
                    f"Index mismatch in {table.name}: "
                    f"missing={sorted(required_indexes - found_indexes)}; "
                    f"extra={sorted(found_indexes - required_indexes)}"
                )
            expected_fk = {
                (column.name, fk.column.table.name, fk.column.name)
                for column in table.columns for fk in column.foreign_keys
            }
            actual_fk = {
                (row[3], row[2], row[4])
                for row in _pragma(db, "foreign_key_list", table.name)
            }
            if expected_fk != actual_fk:
                raise SchemaSafetyError(f"Foreign key mismatch in {table.name}")

        version = None
        if existing_version:
            rows = db.execute("SELECT version_num FROM alembic_version").fetchall()
            if len(rows) != 1 or rows[0][0] != BASELINE_REVISION:
                raise SchemaSafetyError("Unexpected Alembic revision: manual review required")
            version = rows[0][0]
        counts = {
            table: db.execute(f'SELECT count(*) FROM "{table}"').fetchone()[0]
            for table in sorted(expected_tables)
        }
    return {
        "integrity": "ok",
        "revision": version,
        "table_count": len(expected_tables),
        "row_counts": counts,
    }


def verified_backup(source: Path, backup_dir: Path) -> tuple[Path, str]:
    """Consistent SQLite snapshot using sqlite3.backup, including WAL contents."""
    verify_database(source)
    if backup_dir.resolve() == source.resolve():
        raise SchemaSafetyError("Backup directory cannot be the database")
    backup_dir.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
    backup_path = backup_dir / f"{source.stem}-pre006b1-{stamp}-{os.urandom(3).hex()}.db"
    if backup_path.exists():
        raise SchemaSafetyError("Backup destination unexpectedly exists")
    try:
        with _read_only(source) as origin, sqlite3.connect(backup_path) as destination:
            origin.backup(destination, pages=100)
        backup = verify_database(backup_path)
        if backup["revision"] != verify_database(source)["revision"]:
            raise SchemaSafetyError("Backup version differs from source; stop writers")
        sha256 = hashlib.file_digest(backup_path.open("rb"), "sha256").hexdigest()
        return backup_path, sha256
    except Exception:
        backup_path.unlink(missing_ok=True)
        raise


def _config(database: Path) -> Config:
    cfg = Config()
    cfg.set_main_option("script_location", str(PROJECT_ROOT / "migrations"))
    # SQLAlchemy URL handles Windows paths and reserved URL characters.
    url = str(URL.create("sqlite", database=str(database.resolve())))
    cfg.set_main_option("sqlalchemy.url", url.replace("%", "%%"))
    return cfg


def adopt_existing(database: Path, backup_dir: Path, *, confirmed: bool) -> dict:
    if not confirmed:
        raise SchemaSafetyError("Explicit --confirm-offline is required")
    before = verify_database(database)
    if before["revision"] is not None:
        raise SchemaSafetyError("Database already versioned; nothing to adopt")
    saved_path, digest = verified_backup(database, backup_dir)
    # Any concurrent writer is a procedural violation: stop all services first.
    command.stamp(_config(database), BASELINE_REVISION)
    after = verify_database(database)
    if after["revision"] != BASELINE_REVISION or before["row_counts"] != after["row_counts"]:
        raise SchemaSafetyError(
            f"Unexpected schema/row change! Preserve original and backup: {saved_path}"
        )
    return {
        "action": "adopted",
        "revision": BASELINE_REVISION,
        "backup": str(saved_path),
        "backup_sha256": digest,
        "preserved_rows": after["row_counts"],
    }


def create_new(database: Path, *, confirmed: bool) -> dict:
    if not confirmed:
        raise SchemaSafetyError("Explicit --confirm-offline is required")
    if database.exists():
        raise SchemaSafetyError("Refusing to overwrite an existing database")
    database.parent.mkdir(parents=True, exist_ok=True)
    command.upgrade(_config(database), "head")
    outcome = verify_database(database)
    if outcome["revision"] != BASELINE_REVISION:
        raise SchemaSafetyError("New database failed baseline verification")
    return {"action": "created", "database": str(database), **outcome}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Offline SPEC-006B-1 SQLite schema adoption with verified backup"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    parser.add_argument("--backup-dir", type=Path, default=DEFAULT_BACKUPS)
    subparsers = parser.add_subparsers(dest="action", required=True)
    subparsers.add_parser("inspect", help="Read-only strict schema verification")
    subparsers.add_parser("backup", help="Consistent verified SQLite backup")
    for action in ("adopt", "create"):
        subparsers.add_parser(action).add_argument(
            "--confirm-offline", action="store_true",
            help="I confirm API, Vite and dispatcher are stopped",
        )
    args = parser.parse_args(argv)
    try:
        if args.action == "inspect":
            result = {"action": "inspect", **verify_database(args.database)}
        elif args.action == "backup":
            target, digest = verified_backup(args.database, args.backup_dir)
            result = {"action": "backup", "path": str(target), "sha256": digest}
        elif args.action == "adopt":
            result = adopt_existing(args.database, args.backup_dir,
                                    confirmed=args.confirm_offline)
        else:
            result = create_new(args.database, confirmed=args.confirm_offline)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    except (SchemaSafetyError, OSError, sqlite3.Error) as exc:
        parser.exit(2, f"[SPEC-006B-1] ABORTED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
