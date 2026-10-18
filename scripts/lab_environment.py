"""Isolated Windows QA lab for the one-command Handoff launcher.

Only disposable, explicitly named directories directly under the OS TEMP folder
are accepted. This module must never adopt/stamp/upgrade the original POC DB.
"""
from __future__ import annotations

import argparse
import json
import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from handoff_hub.poc_db import make_session_factory
from handoff_hub.schema_admin import SECURITY_REVISION, create_new, verify_database
from handoff_hub.seed_demo_auth import provision

LAB_PREFIX = "handoff-qa-006b4-"
EXPECTED_TABLES = 22
EXPECTED_ACCOUNTS = 5
EXPECTED_QUEUES = 2


class LabSafetyError(RuntimeError):
    """Refuse unsafe or invalid lab paths before any write."""


@dataclass(frozen=True)
class LabEnvironment:
    directory: Path
    database: Path
    credentials: Path
    created: bool

    @property
    def database_url(self) -> str:
        return f"sqlite:///{self.database.as_posix()}"


def validate_lab_dir(raw: str | Path) -> Path:
    """Only an actual directory immediately under TEMP; no path escapes."""
    directory = Path(raw).expanduser().resolve(strict=True)
    temp_root = Path(tempfile.gettempdir()).resolve(strict=True)
    if (
        not directory.is_dir()
        or directory.parent != temp_root
        or not directory.name.startswith(LAB_PREFIX)
        or len(directory.name) <= len(LAB_PREFIX)
    ):
        raise LabSafetyError("Expected a dedicated handoff-qa-006b4-* folder under TEMP")
    return directory


def validate_lab(raw: str | Path) -> LabEnvironment:
    """Inspect an existing 006b4 lab without seed, migration or file mutation."""
    directory = validate_lab_dir(raw)
    database = directory / "synthetic.db"
    credentials = directory / "synthetic-credentials.txt"
    if (
        database.is_symlink() or credentials.is_symlink()
        or not database.is_file() or not credentials.is_file()
    ):
        raise LabSafetyError("Synthetic SQLite/credentials missing or linked outside TEMP")
    state = verify_database(database)
    if (
        state["integrity"] != "ok"
        or state["revision"] != SECURITY_REVISION
        or state["table_count"] != EXPECTED_TABLES
        or state["row_counts"]["auth_users"] != EXPECTED_ACCOUNTS
        or state["row_counts"]["queues"] != EXPECTED_QUEUES
    ):
        raise LabSafetyError("Existing laboratory is not the expected seeded 006b4 DB")
    return LabEnvironment(directory, database, credentials, created=False)


def prepare_lab() -> LabEnvironment:
    """Create a new disposable DB and local passwords; no default-POC writes."""
    directory = validate_lab_dir(tempfile.mkdtemp(prefix=LAB_PREFIX))
    database = directory / "synthetic.db"
    credentials = directory / "synthetic-credentials.txt"
    try:
        create_new(database, confirmed=True)  # only a new nonexistent TEMP DB
        factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
        try:
            names = provision(factory, credentials)
            if len(names) != EXPECTED_ACCOUNTS:
                raise LabSafetyError("Synthetic seed failed to create five accounts")
        finally:
            engine.dispose()
        validate_lab(directory)
    except Exception:  # noqa: BLE001 — cleanup newly created TEMP only, then rethrow
        shutil.rmtree(directory)
        raise
    return LabEnvironment(directory, database, credentials, created=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="TEMP-only QA laboratory")
    parser.add_argument("action", choices=("create", "resume"))
    parser.add_argument("--lab-dir")
    args = parser.parse_args()
    if args.action == "resume" and not args.lab_dir:
        parser.error("resume requires --lab-dir")
    if args.action == "create" and args.lab_dir:
        parser.error("create does not take --lab-dir")
    lab = validate_lab(args.lab_dir) if args.action == "resume" else prepare_lab()
    # No password or token is ever printed by the lab initializer.
    print(json.dumps({
        "directory": str(lab.directory),
        "database_url": lab.database_url,
        "credentials": str(lab.credentials),
        "created": lab.created,
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
