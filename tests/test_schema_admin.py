"""SPEC-006B-1: safe Alembic adoption of existing SQLite POC databases."""
import hashlib
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect, select

from handoff_hub.poc_db import (
    HandoffSession,
    Message,
    QueueMembership,
    make_session_factory,
)
from handoff_hub.schema_admin import (
    AUDIT_REVISION,
    BASELINE_REVISION,
    LATEST_REVISION,
    PROVENANCE_REVISION,
    SECURITY_REVISION,
    SchemaSafetyError,
    _config,
    adopt_existing,
    create_new,
    upgrade_audit_existing,
    upgrade_existing,
    upgrade_security_existing,
    verified_backup,
    verify_database,
)
from handoff_hub.seed_demo_auth import provision


def legacy_database(tmp_path):
    directory = tmp_path / "POC SQLite legado"
    directory.mkdir()
    path = directory / "handoff-poc.db"
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    provision(factory, directory / "credentials.txt")
    with factory.begin() as db:
        handoff = HandoffSession(
            id="historic-n1",
            operation_id="demo",
            integration_id="demo-bot",
            queue_id="n1",
            requester_label="Pessoa com histórico",
            subject="Mensagem e transferência não devem se perder",
            external_conversation_id="legacy-chat",
            idempotency_key="legacy-key",
            status="ACTIVE",
            operator_id="op-ana",
        )
        db.add(handoff)
        db.flush()
        db.add(Message(
            id="historic-message",
            session_id=handoff.id,
            sender="USER",
            content="Mensagem sensível de teste preservada",
            external_message_id="legacy-event",
        ))
    engine.dispose()
    return path


def test_inspect_existing_schema_is_readonly(tmp_path):
    path = legacy_database(tmp_path)
    before = path.read_bytes()
    state = verify_database(path)
    assert state["integrity"] == "ok"
    assert state["revision"] is None
    assert state["table_count"] >= 14
    assert state["row_counts"]["messages"] == 1
    assert state["row_counts"]["queue_memberships"] == 2
    assert path.read_bytes() == before
    with sqlite3.connect(path) as db:
        assert not db.execute(
            "SELECT name FROM sqlite_master WHERE name='alembic_version'"
        ).fetchall()


def test_adoption_has_verified_backup_and_preserves_all_rows(tmp_path):
    path = legacy_database(tmp_path)
    original = verify_database(path)
    backup_directory = tmp_path / "secure backup"
    with pytest.raises(SchemaSafetyError, match="confirm-offline"):
        adopt_existing(path, backup_directory, confirmed=False)
    assert not backup_directory.exists()
    result = adopt_existing(path, backup_directory, confirmed=True)
    assert result["action"] == "adopted"
    assert result["revision"] == BASELINE_REVISION
    backup = next(backup_directory.glob("*.db"))
    assert str(backup) == result["backup"]
    assert len(result["backup_sha256"]) == 64
    backup_state = verify_database(backup)
    final_state = verify_database(path)
    assert backup_state["revision"] is None
    assert final_state["revision"] == BASELINE_REVISION
    assert backup_state["row_counts"] == original["row_counts"]
    assert final_state["row_counts"] == original["row_counts"]
    with sqlite3.connect(path) as db:
        assert db.execute(
            "SELECT content FROM messages WHERE id='historic-message'"
        ).fetchone()[0] == "Mensagem sensível de teste preservada"
    with pytest.raises(SchemaSafetyError, match="already versioned"):
        adopt_existing(path, backup_directory, confirmed=True)
    assert len(list(backup_directory.glob("*.db"))) == 1


def test_create_fresh_versioned_sqlite_and_preserve_normal_seed(tmp_path):
    path = tmp_path / "new install" / "fresh.db"
    with pytest.raises(SchemaSafetyError, match="confirm-offline"):
        create_new(path, confirmed=False)
    assert not path.exists()
    result = create_new(path, confirmed=True)
    assert result["revision"] == LATEST_REVISION
    assert result["row_counts"]["queues"] == 0
    assert result["row_counts"]["session_queue_segments"] == 0
    assert result["row_counts"]["message_queue_provenance"] == 0
    assert result["row_counts"]["session_event_queue_provenance"] == 0
    assert result["row_counts"]["history_access_audit"] == 0
    assert result["row_counts"]["security_decisions"] == 0
    with pytest.raises(SchemaSafetyError, match="overwrite"):
        create_new(path, confirmed=True)
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    try:
        provision(factory, tmp_path / "new-credentials.txt")
        with factory() as db:
            assert db.get(HandoffSession, "historic-n1") is None
            assert set(db.scalars(select(QueueMembership.queue_id)).all()) == {"n1", "n2"}
        assert verify_database(path)["row_counts"]["auth_users"] == 5
    finally:
        engine.dispose()


def test_reject_partial_or_unknown_schema_without_mutation(tmp_path):
    path = tmp_path / "partial.db"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE operations (id VARCHAR(40) PRIMARY KEY)")
        db.commit()
    before = path.read_bytes()
    with pytest.raises(SchemaSafetyError, match="Unrecognized POC schema"):
        adopt_existing(path, tmp_path / "backups", confirmed=True)
    assert path.read_bytes() == before
    assert not (tmp_path / "backups").exists()


def test_reject_changed_columns_and_missing_indexes(tmp_path):
    path = legacy_database(tmp_path)
    with sqlite3.connect(path) as db:
        db.execute("DROP INDEX ix_queues_operation")
        db.commit()
    with pytest.raises(SchemaSafetyError, match="Index mismatch"):
        verify_database(path)
    with pytest.raises(SchemaSafetyError, match="Index mismatch"):
        verified_backup(path, tmp_path / "backups")
    assert not (tmp_path / "backups").exists()


def test_backup_is_consistent_without_changing_original(tmp_path):
    path = legacy_database(tmp_path)
    initial = verify_database(path)
    backup_path, digest = verified_backup(path, tmp_path / "backups")
    assert len(digest) == 64
    assert backup_path != path
    assert '-preunversioned-' in backup_path.name
    assert verify_database(backup_path) == initial
    assert hashlib.sha256(backup_path.read_bytes()).hexdigest() == digest
    assert verify_database(path) == initial


def test_upgrade_006b1_to_006b2_keeps_legacy_records(tmp_path):
    db_path = legacy_database(tmp_path)
    backups = tmp_path / "backups"
    adopt_existing(db_path, backups, confirmed=True)
    prior = verify_database(db_path)
    assert prior["revision"] == BASELINE_REVISION
    with pytest.raises(SchemaSafetyError, match="confirm-offline"):
        upgrade_existing(db_path, backups, confirmed=False)
    upgraded = upgrade_existing(db_path, backups, confirmed=True)
    after = verify_database(db_path)
    assert upgraded["revision"] == PROVENANCE_REVISION
    assert "-pre006b1-" in Path(upgraded["backup"]).name
    assert verify_database(Path(upgraded["backup"]))["revision"] == BASELINE_REVISION
    assert after["revision"] == PROVENANCE_REVISION
    assert after["table_count"] == prior["table_count"] + 3
    assert after["row_counts"]["handoff_sessions"] == 1
    assert after["row_counts"]["messages"] == 1
    assert all(after["row_counts"][name] == count
               for name, count in prior["row_counts"].items())
    assert upgraded["provenance_tables_empty"] is True
    assert all(after["row_counts"][name] == 0 for name in (
        "session_queue_segments",
        "message_queue_provenance",
        "session_event_queue_provenance",
    ))
    with sqlite3.connect(db_path) as db:
        assert db.execute(
            "SELECT content FROM messages WHERE id='historic-message'"
        ).fetchone()[0] == "Mensagem sensível de teste preservada"
    with pytest.raises(SchemaSafetyError, match="requires a verified"):
        upgrade_existing(db_path, backups, confirmed=True)


def test_queue_provenance_constraints_require_valid_parents(tmp_path):
    db_path = tmp_path / "schema.db"
    create_new(db_path, confirmed=True)
    with sqlite3.connect(db_path) as conn:
        conn.execute("PRAGMA foreign_keys=ON")
        with pytest.raises(sqlite3.IntegrityError):
            conn.execute(
                "INSERT INTO session_queue_segments "
                "(id, session_id, queue_id, ordinal, started_at, provenance_state) "
                "VALUES ('seg1', 'does-not-exist', 'n1', 0, "
                "'2026-10-16 13:00:00', 'UNDETERMINED')"
            )
        assert conn.execute(
            "SELECT COUNT(*) FROM session_queue_segments"
        ).fetchone()[0] == 0


def test_upgrade_rejects_unversioned_legacy_database(tmp_path):
    db_path = legacy_database(tmp_path)
    before = verify_database(db_path)
    backup_dir = tmp_path / "backups"
    with pytest.raises(SchemaSafetyError, match="requires a verified"):
        upgrade_existing(db_path, backup_dir, confirmed=True)
    assert verify_database(db_path) == before
    assert not backup_dir.exists()


def test_versioned_006b2_backup_is_independently_inspectable(tmp_path):
    path = tmp_path / "fresh.db"
    create_new(path, confirmed=True)
    backup_path, checksum = verified_backup(path, tmp_path / "backups")
    assert len(checksum) == 64
    assert verify_database(backup_path)["revision"] == SECURITY_REVISION
    assert "-pre006b4-" in backup_path.name
    assert verify_database(path) == verify_database(backup_path)


def test_poc_startup_does_not_create_migration_owned_tables(tmp_path):
    """The POC launcher must not silently install 006B-2 DDL."""
    database = tmp_path / "unversioned-startup.db"
    _, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    try:
        created = set(inspect(engine).get_table_names())
        assert "session_queue_segments" not in created
        assert "message_queue_provenance" not in created
        assert "session_event_queue_provenance" not in created
        assert "alembic_version" not in created
        assert "history_access_audit" not in created
        assert "security_decisions" not in created
        assert verify_database(database)["revision"] is None
    finally:
        engine.dispose()


def test_new_schema_validator_detects_missing_provenance_index(tmp_path):
    database = tmp_path / "tampered-006b2.db"
    create_new(database, confirmed=True)
    with sqlite3.connect(database) as db:
        db.execute("DROP INDEX ix_segments_queue_started")
        db.commit()
    with pytest.raises(SchemaSafetyError, match="Index mismatch"):
        verify_database(database)


def test_audit_revision_requires_explicit_offline_upgrade_and_preserves_rows(tmp_path):
    db_path = legacy_database(tmp_path)
    backups = tmp_path / "safe-backups"
    original = verify_database(db_path)
    with pytest.raises(SchemaSafetyError, match="requires a verified"):
        upgrade_audit_existing(db_path, backups, confirmed=True)
    assert not backups.exists()
    adopt_existing(db_path, backups, confirmed=True)
    upgrade_existing(db_path, backups, confirmed=True)
    before = verify_database(db_path)
    assert before["revision"] == PROVENANCE_REVISION
    with pytest.raises(SchemaSafetyError, match="confirm-offline"):
        upgrade_audit_existing(db_path, backups, confirmed=False)
    assert verify_database(db_path) == before
    result = upgrade_audit_existing(db_path, backups, confirmed=True)
    after = verify_database(db_path)
    assert result["revision"] == AUDIT_REVISION
    assert "-pre006b2-" in Path(result["backup"]).name
    assert result["audit_table_empty"] is True
    assert len(result["backup_sha256"]) == 64
    assert after["revision"] == AUDIT_REVISION
    assert after["table_count"] == original["table_count"] + 4
    assert after["row_counts"]["history_access_audit"] == 0
    assert all(after["row_counts"][table] == amount
               for table, amount in before["row_counts"].items())
    assert verify_database(db_path)["row_counts"]["messages"] == 1
    with pytest.raises(SchemaSafetyError, match="requires a verified"):
        upgrade_audit_existing(db_path, backups, confirmed=True)


def test_audit_schema_validator_detects_missing_index(tmp_path):
    path = tmp_path / "audit-index.db"
    create_new(path, confirmed=True)
    with sqlite3.connect(path) as conn:
        conn.execute("DROP INDEX ix_history_audit_user_time")
        conn.commit()
    with pytest.raises(SchemaSafetyError, match="Index mismatch"):
        verify_database(path)


def test_security_upgrade_requires_versioned_audit_database_and_verified_backup(tmp_path):
    path = tmp_path / "security-upgrade.db"
    create_new(path, confirmed=True)
    assert verify_database(path)["revision"] == SECURITY_REVISION
    # Downgrade only the newly created, empty disposable database.
    command.downgrade(_config(path), AUDIT_REVISION)
    before = verify_database(path)
    assert before["revision"] == AUDIT_REVISION
    backup_dir = tmp_path / "security-backups"
    with pytest.raises(SchemaSafetyError, match="confirm-offline"):
        upgrade_security_existing(path, backup_dir, confirmed=False)
    assert not backup_dir.exists()
    upgraded = upgrade_security_existing(path, backup_dir, confirmed=True)
    after = verify_database(path)
    assert upgraded["revision"] == SECURITY_REVISION
    assert "-pre006b3-" in Path(upgraded["backup"]).name
    assert upgraded["security_table_empty"] is True
    assert after["table_count"] == before["table_count"] + 1
    assert after["row_counts"]["security_decisions"] == 0
    assert all(after["row_counts"][name] == count
               for name, count in before["row_counts"].items())
    assert len(upgraded["backup_sha256"]) == 64
    with pytest.raises(SchemaSafetyError, match="requires verified"):
        upgrade_security_existing(path, backup_dir, confirmed=True)


def test_security_revision_rejects_missing_index_and_legacy_schema_stays_closed(tmp_path):
    path = tmp_path / "security-index.db"
    create_new(path, confirmed=True)
    with sqlite3.connect(path) as db:
        db.execute("DROP INDEX ix_security_decisions_actor_time")
        db.commit()
    with pytest.raises(SchemaSafetyError, match="Index mismatch"):
        verify_database(path)
    legacy = legacy_database(tmp_path)
    original = verify_database(legacy)
    with pytest.raises(SchemaSafetyError, match="requires verified"):
        upgrade_security_existing(legacy, tmp_path / "no-backups", confirmed=True)
    assert verify_database(legacy) == original
    assert original["revision"] is None
    assert original["table_count"] == 17
