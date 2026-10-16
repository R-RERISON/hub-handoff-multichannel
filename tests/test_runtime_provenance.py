"""SPEC-006B-3 runtime queue provenance; all SQLite files are disposable tmp_path DBs."""
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    HandoffSession,
    Message,
    make_session_factory,
)
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
