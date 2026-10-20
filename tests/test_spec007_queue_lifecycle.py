"""SPEC-007/A1.2 migration and lifecycle acceptance, synthetic SQLite only."""
from __future__ import annotations

import hashlib
import sqlite3
from pathlib import Path

import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.auto_dispatch import run_dispatch_cycle
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    QueueMembership,
    make_session_factory,
)
from handoff_hub.provenance_writer import ProvenanceRecorder
from handoff_hub.queue_lifecycle_schema import LIFECYCLE_REVISION
from handoff_hub.schema_admin import (
    SECURITY_REVISION,
    SchemaSafetyError,
    _config,
    upgrade_lifecycle_existing,
    verify_database,
)
from scripts import lab_environment
from scripts.release_grant_toggle import bearer

KEY = "qa-lifecycle-only"


def lab_ready(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    lab = lab_environment.prepare_lab()
    return lab


def upgraded(lab, tmp_path):
    result = upgrade_lifecycle_existing(
        lab.database, tmp_path / "backups", confirmed=True,
    )
    assert result["revision"] == LIFECYCLE_REVISION
    return result


def login(client, lab, username):
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            identity = db.scalar(select(AuthUser).where(AuthUser.username == username))
            assert identity is not None
            uid = identity.id
    finally:
        engine.dispose()
    return bearer(client, lab.credentials, username, uid)


def create(client, admin, queue_id):
    return client.post("/v1/admin/queues", headers=admin, json={
        "id": queue_id, "name": "Fila " + queue_id,
    })


def transition(client, admin, queue_id, state, version):
    return client.patch(
        f"/v1/admin/queues/{queue_id}/state", headers=admin,
        json={"state": state, "expected_version": version},
    )


def rows(lab, queue_id):
    with sqlite3.connect(lab.database.as_uri() + "?mode=ro", uri=True) as db:
        current = db.execute(
            "SELECT state,version FROM queue_lifecycle WHERE queue_id=?",
            (queue_id,),
        ).fetchone()
        entries = db.execute(
            "SELECT from_state,to_state,version FROM queue_lifecycle_events "
            "WHERE queue_id=? ORDER BY version",
            (queue_id,),
        ).fetchall()
        return current, entries


def ticket(client, queue_id, suffix):
    return client.post(
        "/v1/handoffs",
        headers={"X-POC-Key": KEY, "Idempotency-Key": "test-a2-" + suffix},
        json={
            "queue_id": queue_id,
            "external_conversation_id": "case-" + suffix,
            "requester_label": "QA synthetic person",
            "subject": "Queue lifecycle validation",
        },
    )


def test_migration_is_explicit_offline_verified_and_never_backfills(
    tmp_path, monkeypatch,
):
    lab = lab_ready(tmp_path, monkeypatch)
    before = verify_database(lab.database)
    assert before["revision"] == SECURITY_REVISION
    with pytest.raises(SchemaSafetyError, match="confirm-offline"):
        upgrade_lifecycle_existing(lab.database, tmp_path / "backups", confirmed=False)
    assert verify_database(lab.database) == before
    assert not (tmp_path / "backups").exists()
    result = upgraded(lab, tmp_path)
    after = verify_database(lab.database)
    assert result["lifecycle_tables_empty"] is True
    assert "-pre006b4-" in Path(result["backup"]).name
    preupgrade = Path(result["backup"])
    assert verify_database(preupgrade) == before
    assert hashlib.sha256(preupgrade.read_bytes()).hexdigest() == result["backup_sha256"]
    assert after["revision"] == LIFECYCLE_REVISION
    assert all(after["row_counts"][name] == count
               for name, count in before["row_counts"].items())
    assert after["row_counts"]["queue_lifecycle"] == 0
    assert after["row_counts"]["queue_lifecycle_events"] == 0
    _factory, engine = make_session_factory(lab.database_url)
    try:
        assert ProvenanceRecorder(engine).queue_lifecycle_enabled is True
    finally:
        engine.dispose()
    with pytest.raises(SchemaSafetyError, match="requires verified"):
        upgrade_lifecycle_existing(lab.database, tmp_path / "again", confirmed=True)


def test_draft_requires_explicit_activation_and_blocks_intake_and_offer(
    tmp_path, monkeypatch,
):
    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        made = create(c, admin, "n3")
        assert made.status_code == 201, made.text
        assert rows(lab, "n3") == (
            ("DRAFT", 1), [(None, "DRAFT", 1)],
        )
        overview = c.get("/v1/admin/overview", headers=admin).json()
        n3 = next(q for q in overview["queues"] if q["id"] == "n3")
        assert n3["lifecycle_state"] == "DRAFT"
        assert n3["lifecycle_version"] == 1
        assert overview["capabilities"]["queue_lifecycle_available"] is True
        assert ticket(c, "n3", "draft").status_code == 409
        offer = c.post("/v1/dispatch/offer", headers={"X-POC-Key": KEY}, json={
            "queue_id": "n3", "operation_id": "demo",
        })
        assert offer.status_code == 409
        active = transition(c, admin, "n3", "ACTIVE", 1)
        assert active.status_code == 200, active.text
        assert active.json()["version"] == 2
        assert ticket(c, "n3", "active").status_code == 201
        blocked = transition(c, admin, "n3", "PAUSED", 2)
        assert blocked.status_code == 409
        assert rows(lab, "n3")[0] == ("ACTIVE", 2)


def test_state_cas_pause_archive_and_routing_fail_closed(
    tmp_path, monkeypatch,
):
    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        assert create(c, admin, "n4").status_code == 201
        assert transition(c, admin, "n4", "PAUSED", 1).status_code == 409
        assert transition(c, admin, "n4", "ACTIVE", 0).status_code == 409
        assert transition(c, admin, "n4", "ACTIVE", 1).status_code == 200
        assert transition(c, admin, "n4", "PAUSED", 2).status_code == 200
        assert ticket(c, "n4", "paused").status_code == 409
        assert transition(c, admin, "n4", "ARCHIVED", 3).status_code == 200
        assert transition(c, admin, "n4", "ACTIVE", 4).status_code == 409
        assert ticket(c, "n4", "archived").status_code == 409
        current, events = rows(lab, "n4")
        assert current == ("ARCHIVED", 4)
        assert [record[1] for record in events] == [
            "DRAFT", "ACTIVE", "PAUSED", "ARCHIVED",
        ]
        assert [record[2] for record in events] == [1, 2, 3, 4]
        # Existing n1 from 006b4 remains ACTIVE (version=0) after opt-in.
        overview = c.get("/v1/admin/overview", headers=admin).json()
        old = next(q for q in overview["queues"] if q["id"] == "n1")
        assert (old["lifecycle_state"], old["lifecycle_version"]) == ("ACTIVE", 0)


def test_nonadmin_or_cross_operation_cannot_change_state(tmp_path, monkeypatch):
    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        assert create(c, admin, "n5").status_code == 201
        assert c.patch("/v1/admin/queues/n5/state", json={
            "state": "ACTIVE", "expected_version": 1,
        }).status_code == 401
        for user in ("supervisor.demo", "auditor.demo", "ana.demo"):
            denied = transition(c, login(c, lab, user), "n5", "ACTIVE", 1)
            assert denied.status_code == 403
        assert transition(c, admin, "no-such-queue", "ACTIVE", 0).status_code == 404
        assert rows(lab, "n5")[0] == ("DRAFT", 1)


def test_failed_lifecycle_journal_rolls_back_state_and_version(tmp_path, monkeypatch):
    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        assert create(c, admin, "n6").status_code == 201
        with sqlite3.connect(lab.database) as db:
            db.execute(
                "CREATE TRIGGER qa_refuse_active BEFORE INSERT ON queue_lifecycle_events "
                "WHEN NEW.to_state='ACTIVE' BEGIN "
                "SELECT RAISE(ABORT,'qa lifecycle error'); END"
            )
        failed = transition(c, admin, "n6", "ACTIVE", 1)
        assert failed.status_code == 503
        assert rows(lab, "n6") == (("DRAFT", 1), [(None, "DRAFT", 1)])
        # A populated ledger can never be destructively downgraded.
        with pytest.raises(RuntimeError, match="destructive downgrade"):
            command.downgrade(_config(lab.database), SECURITY_REVISION)


def test_unmigrated_lab_has_no_transition_endpoint_effect(tmp_path, monkeypatch):
    lab = lab_ready(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        result = transition(c, admin, "n1", "PAUSED", 0)
        assert result.status_code == 503
        assert create(c, admin, "n3").status_code == 201
        assert ticket(c, "n3", "legacy").status_code == 201
    assert verify_database(lab.database)["revision"] == SECURITY_REVISION


def test_transfer_rejects_draft_queue_and_does_not_expose_target(
    tmp_path, monkeypatch,
):
    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        assert create(c, admin, "n7").status_code == 201
        original = ticket(c, "n1", "source")
        assert original.status_code == 201, original.text
        sid = original.json()["id"]
        offered = c.post("/v1/dispatch/offer", headers={"X-POC-Key": KEY},
                         json={"queue_id": "n1", "operation_id": "demo"})
        assert offered.status_code == 200
        assert offered.json()["result"] == "offered"
        accepted = c.post(
            f"/v1/handoffs/{sid}/accept", headers={"X-POC-Key": KEY},
            json={"operator_id": "op-ana"},
        )
        assert accepted.status_code == 200
        choices = c.get(
            f"/v1/handoffs/{sid}/transfer-targets",
            headers={"X-POC-Key": KEY},
        )
        assert choices.status_code == 200
        assert "n7" not in {q["id"] for q in choices.json()["destinations"]}
        blocked = c.post(
            f"/v1/handoffs/{sid}/transfer", headers={"X-POC-Key": KEY},
            json={"operator_id": "op-ana", "queue_id": "n7",
                  "reason": "QA teste de fila em rascunho"},
        )
        assert blocked.status_code == 409
        assert rows(lab, "n7")[0] == ("DRAFT", 1)
        assert c.get("/v1/handoffs", headers={"X-POC-Key": KEY}).status_code == 200


def test_auto_dispatch_skips_draft_even_with_synthetic_queued_case(
    tmp_path, monkeypatch,
):
    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    app = create_app(database_url=lab.database_url, api_key=KEY)
    factory, engine = make_session_factory(lab.database_url)
    try:
        with TestClient(app, raise_server_exceptions=False) as c:
            admin = login(c, lab, "admin.demo")
            login(c, lab, "ana.demo")  # Live operator auth lease.
            assert create(c, admin, "n8").status_code == 201
            blocked_manual = c.post(
                "/v1/dispatch/next",
                headers={"X-POC-Key": KEY},
                json={"queue_id": "n8", "operation_id": "demo"},
            )
            assert blocked_manual.status_code == 409
            with factory.begin() as db:
                # Deliberate synthetic bypass of intake for dispatch regression.
                db.add(QueueMembership(queue_id="n8", operator_id="op-ana"))
                db.add(HandoffSession(
                    operation_id="demo", integration_id="demo-bot",
                    queue_id="n8", external_conversation_id="qa-auto-draft",
                    requester_label="Pessoa sintética", subject="Fila DRAFT",
                    idempotency_key="spec007-auto-draft",
                ))
            assert run_dispatch_cycle(factory)["offered"] == 0
            with factory() as db:
                session = db.scalar(select(HandoffSession).where(
                    HandoffSession.queue_id == "n8",
                ))
                assert session is not None and session.status == "QUEUED"
            assert transition(c, admin, "n8", "ACTIVE", 1).status_code == 200
            assert run_dispatch_cycle(factory)["offered"] == 1
            with factory() as db:
                session = db.scalar(select(HandoffSession).where(
                    HandoffSession.queue_id == "n8",
                ))
                assert session is not None and session.status == "OFFERED"
    finally:
        engine.dispose()

def test_lifecycle_backup_after_upgrade_uses_007a2_source_label(
    tmp_path, monkeypatch,
):
    from handoff_hub.schema_admin import verified_backup

    lab = lab_ready(tmp_path, monkeypatch)
    upgraded(lab, tmp_path)
    current = verify_database(lab.database)
    assert current["revision"] == LIFECYCLE_REVISION
    saved, checksum = verified_backup(lab.database, tmp_path / "snapshot-after")
    assert "-pre007a2-" in saved.name
    assert verify_database(saved) == current
    assert hashlib.sha256(saved.read_bytes()).hexdigest() == checksum
    assert verify_database(lab.database) == current
