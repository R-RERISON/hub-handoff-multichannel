"""SPEC-006B-3 runtime queue provenance; all SQLite files are disposable tmp_path DBs."""
from datetime import timedelta

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.auto_dispatch import run_dispatch_cycle
from handoff_hub.poc_api import create_app
from handoff_hub.poc_auth import naive_utc
from handoff_hub.poc_db import (
    HandoffOffer,
    HandoffSession,
    Message,
    SessionEvent,
    make_session_factory,
)
from handoff_hub.provenance_audit import provenance_report
from handoff_hub.provenance_schema import (
    MESSAGE_QUEUE_PROVENANCE,
    SESSION_EVENT_QUEUE_PROVENANCE,
    SESSION_QUEUE_SEGMENTS,
)
from handoff_hub.schema_admin import (
    adopt_existing,
    create_new,
    upgrade_existing,
)
from handoff_hub.seed_demo_auth import provision

HEADERS = {"X-POC-Key": "legacy-test-key"}


def setup_versioned(tmp_path):
    path = tmp_path / "versioned.db"
    create_new(path, confirmed=True)
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    provision(factory, tmp_path / "demo-secrets.txt")
    engine.dispose()
    return path, factory


def create_ticket(client, suffix):
    response = client.post(
        "/v1/handoffs",
        headers={**HEADERS, "Idempotency-Key": f"provenance-{suffix}"},
        json={
            "requester_label": "Pessoa solicitante",
            "subject": "Fila segmentada",
            "external_conversation_id": f"conversa-{suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def new_message(client, hid, sender, label, operator_id=None):
    payload = {
        "sender": sender,
        "content": label,
        "external_message_id": f"external-{label}",
    }
    if operator_id is not None:
        payload["operator_id"] = operator_id
    result = client.post(
        f"/v1/handoffs/{hid}/messages",
        headers=HEADERS,
        json=payload,
    )
    assert result.status_code == 201, result.text
    return result.json()["id"]


def assigned(factory, hid, operator_id):
    with factory.begin() as db:
        h = db.get(HandoffSession, hid)
        h.status = "ACTIVE"
        h.operator_id = operator_id


def test_new_ticket_messages_transfer_follow_verified_queue_segments(tmp_path):
    path, factory = setup_versioned(tmp_path)
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "fresh")
        first_message = new_message(client, hid, "USER", "solicitacao-n1")
        assigned(factory, hid, "op-ana")
        second_message = new_message(client, hid, "OPERATOR", "orientacao-n1", "op-ana")

        transfer = client.post(
            f"/v1/handoffs/{hid}/transfer", headers=HEADERS,
            json={
                "operator_id": "op-ana", "queue_id": "n2",
                "reason": "Orientacao interna N1 para N2",
            },
        )
        assert transfer.status_code == 200, transfer.text
        assert transfer.json()["status"] == "QUEUED"
        third_message = new_message(client, hid, "USER", "nova-duvida-n2")
        # Duplicate request does not create a second provenance record.
        response = client.post(
            f"/v1/handoffs/{hid}/messages", headers=HEADERS,
            json={"sender": "USER", "content": "nova-duvida-n2",
                  "external_message_id": "external-nova-duvida-n2"},
        )
        assert response.status_code == 201
        assert response.json()["status"] == "duplicate"

    with factory() as db:
        segments = db.execute(
            select(SESSION_QUEUE_SEGMENTS)
            .where(SESSION_QUEUE_SEGMENTS.c.session_id == hid)
            .order_by(SESSION_QUEUE_SEGMENTS.c.ordinal)
        ).mappings().all()
        assert len(segments) == 2
        first, second = segments
        assert (first["queue_id"], first["ordinal"], first["provenance_state"]) == (
            "n1", 0, "VERIFIED"
        )
        assert first["ended_at"] is not None
        assert (second["queue_id"], second["ordinal"], second["provenance_state"]) == (
            "n2", 1, "VERIFIED"
        )
        assert second["ended_at"] is None
        assert second["transfer_id"] is not None
        assert second["started_at"] == first["ended_at"]
        references = {
            row["message_id"]: row
            for row in db.execute(select(MESSAGE_QUEUE_PROVENANCE)).mappings()
        }
        assert len(references) == 3
        assert references[first_message]["segment_id"] == first["id"]
        assert references[second_message]["segment_id"] == first["id"]
        assert references[third_message]["segment_id"] == second["id"]
        assert all(row["confidence"] == "VERIFIED" for row in references.values())
        transfer_events = db.execute(select(SESSION_EVENT_QUEUE_PROVENANCE)).mappings().all()
        assert len(transfer_events) == 2  # QUEUED + TRANSFERRED
        assert all(row["confidence"] == "VERIFIED" for row in transfer_events)


def test_preexisting_unsegmented_ticket_does_not_gain_forged_queue_history(tmp_path):
    path = tmp_path / "legacy.db"
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    provision(factory, tmp_path / "secrets.txt")
    engine.dispose()
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "legacy")
        old_message = new_message(client, hid, "USER", "pre-migration-msg")
        assigned(factory, hid, "op-ana")

    adopt_existing(path, tmp_path / "backup-baseline", confirmed=True)
    upgrade_existing(path, tmp_path / "backup-upgrade", confirmed=True)
    # Reopen the app AFTER migration; never activate recorder against stale engine.
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        new_message_id = new_message(client, hid, "USER", "unknown-legacy-n1")
        transferred = client.post(
            f"/v1/handoffs/{hid}/transfer", headers=HEADERS,
            json={"operator_id": "op-ana", "queue_id": "n2",
                  "reason": "Escalonamento de ticket legado"},
        )
        assert transferred.status_code == 200, transferred.text
        after_transfer = new_message(client, hid, "USER", "known-n2")
    with factory() as db:
        segments = db.execute(select(SESSION_QUEUE_SEGMENTS)).mappings().all()
        assert len(segments) == 1
        assert segments[0]["queue_id"] == "n2"
        assert segments[0]["ordinal"] == 0
        assert segments[0]["provenance_state"] == "VERIFIED"
        refs = {
            row["message_id"]: row
            for row in db.execute(select(MESSAGE_QUEUE_PROVENANCE)).mappings()
        }
        assert old_message not in refs  # No automatic historical backfill.
        assert refs[new_message_id]["segment_id"] is None
        assert refs[new_message_id]["confidence"] == "UNDETERMINED"
        assert refs[after_transfer]["segment_id"] == segments[0]["id"]
        assert refs[after_transfer]["confidence"] == "VERIFIED"


def test_unversioned_database_does_not_create_provenance_tables(tmp_path):
    path = tmp_path / "legacy-active.db"
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    provision(factory, tmp_path / "passwords.txt")
    engine.dispose()
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "unversioned")
        new_message(client, hid, "USER", "still-works")
    with factory() as db:
        message = db.scalar(select(Message).where(Message.session_id == hid))
        assert message is not None
        tables = set(db.connection().exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).scalars())
        assert "session_queue_segments" not in tables
        assert "message_queue_provenance" not in tables
        assert "session_event_queue_provenance" not in tables


def test_failed_transfer_keeps_existing_segment_open(tmp_path):
    path, factory = setup_versioned(tmp_path)
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "failed-transfer")
        assigned(factory, hid, "op-ana")
        rejected = client.post(
            f"/v1/handoffs/{hid}/transfer", headers=HEADERS,
            json={"operator_id": "op-ana", "queue_id": "n1",
                  "reason": "Destino igual a origem"},
        )
        assert rejected.status_code == 422
    with factory() as db:
        segments = db.execute(
            select(SESSION_QUEUE_SEGMENTS).where(SESSION_QUEUE_SEGMENTS.c.session_id == hid)
        ).mappings().all()
        assert len(segments) == 1
        assert segments[0]["queue_id"] == "n1"
        assert segments[0]["ended_at"] is None


def test_baseline_only_db_keeps_recorder_disabled(tmp_path):
    path = tmp_path / "baseline-only.db"
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    provision(factory, tmp_path / "baseline-credentials.txt")
    engine.dispose()
    adopt_existing(path, tmp_path / "baseline-backup", confirmed=True)
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "baseline")
        new_message(client, hid, "USER", "baseline-user-message")
    with factory() as db:
        message = db.scalar(select(Message).where(Message.session_id == hid))
        assert message is not None
        tables = set(db.connection().exec_driver_sql(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).scalars())
        assert "session_queue_segments" not in tables


def test_operational_events_are_provenanced_for_manual_offer_and_close(tmp_path):
    path, factory = setup_versioned(tmp_path)
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "operational")
        offer = client.post(
            "/v1/dispatch/offer", headers=HEADERS, json={"queue_id": "n1"}
        ).json()
        assert offer["result"] == "offered"
        accepted = client.post(
            f"/v1/handoffs/{hid}/accept", headers=HEADERS,
            json={"operator_id": "op-ana"},
        )
        assert accepted.status_code == 200, accepted.text
        closed = client.post(
            f"/v1/operators/op-ana/handoffs/{hid}/close", headers=HEADERS,
        )
        assert closed.status_code == 200, closed.text
    with factory() as db:
        events = db.scalars(
            select(SessionEvent).where(SessionEvent.session_id == hid)
            .order_by(SessionEvent.created_at, SessionEvent.id)
        ).all()
        assert {"QUEUED", "OFFERED", "ACCEPTED", "CLOSED"} == {
            e.event_type for e in events
        }
        tagged = {
            row["event_id"]: row
            for row in db.execute(select(SESSION_EVENT_QUEUE_PROVENANCE)).mappings()
        }
        assert set(tagged) == {e.id for e in events}
        assert all(entry["confidence"] == "VERIFIED" for entry in tagged.values())
        assert len({entry["segment_id"] for entry in tagged.values()}) == 1
    report = provenance_report(path)
    assert report["status"] == "REPORT_READY"
    assert report["event_coverage"] == {
        "verified": 4, "undetermined": 0, "uncovered": 0,
    }
    assert report["safe_for_history_authorization"] is False


def test_automatic_offer_and_timeout_events_are_attributed(tmp_path):
    path, factory = setup_versioned(tmp_path)
    password_text = (tmp_path / "demo-secrets.txt").read_text(encoding="utf-8")
    password = next(
        line.split("]: ", 1)[1] for line in password_text.splitlines()
        if line.startswith("ana.demo [")
    )
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        auth = client.post("/v1/auth/login", json={
            "username": "ana.demo", "password": password,
        })
        assert auth.status_code == 200, auth.text
        hid = create_ticket(client, "autodispatch")
        first_cycle = run_dispatch_cycle(factory)
        assert first_cycle["offered"] == 1
        with factory.begin() as db:
            offer = db.scalar(
                select(HandoffOffer).where(HandoffOffer.session_id == hid)
            )
            assert offer is not None
            offer.expires_at = naive_utc() - timedelta(seconds=1)
        second_cycle = run_dispatch_cycle(factory)
        assert second_cycle["expired"] >= 1
    with factory() as db:
        events = db.scalars(
            select(SessionEvent).where(SessionEvent.session_id == hid)
        ).all()
        assert {"QUEUED", "OFFERED_AUTO", "OFFER_EXPIRED"}.issubset(
            {e.event_type for e in events}
        )
        tagged = {
            row["event_id"]: row
            for row in db.execute(select(SESSION_EVENT_QUEUE_PROVENANCE)).mappings()
        }
        assert all(event.id in tagged for event in events)
        assert all(tagged[event.id]["confidence"] == "VERIFIED" for event in events)


def test_readonly_legacy_audit_never_backfills_or_reads_message_content(tmp_path):
    path = tmp_path / "legacy-audit.db"
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    provision(factory, tmp_path / "creds.txt")
    engine.dispose()
    with TestClient(create_app(database_url=f"sqlite:///{path.as_posix()}",
                               api_key="legacy-test-key")) as client:
        hid = create_ticket(client, "audit")
        new_message(client, hid, "USER", "confidential-marker-only-for-test")

    legacy_report = provenance_report(path)
    assert legacy_report["status"] == "NOT_MIGRATED"
    assert "confidential-marker-only-for-test" not in str(legacy_report)
    adopt_existing(path, tmp_path / "backups-before", confirmed=True)
    upgrade_existing(path, tmp_path / "backups-upgrade", confirmed=True)
    before = provenance_report(path)
    assert before["status"] == "REPORT_READY"
    assert before["message_coverage"]["uncovered"] == 1
    assert before["event_coverage"]["uncovered"] == 1
    assert before["sessions_without_segments"] == 1
    assert before["safe_for_history_authorization"] is False
    after = provenance_report(path)
    assert after == before
    assert "confidential-marker-only-for-test" not in str(after)
