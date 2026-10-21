"""RC-001 operational golden path: A1.2 admin + N1/N2 verified handoff, TEMP only."""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, make_session_factory
from handoff_hub.queue_lifecycle_schema import LIFECYCLE_REVISION
from handoff_hub.schema_admin import upgrade_lifecycle_existing, verify_database
from scripts import lab_environment
from scripts.release_grant_toggle import bearer

KEY = "rc001-operations-synthetic-in-process"
CLIENT_HEADERS = {"X-POC-Key": KEY}


def persona(client, lab, name):
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            user_id = db.scalar(select(AuthUser.id).where(AuthUser.username == name))
            assert user_id is not None
    finally:
        engine.dispose()
    return bearer(client, lab.credentials, name, user_id)


def test_admin_lifecycle_n1_n2_transfer_and_verified_history(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    lab = lab_environment.prepare_lab()
    assert verify_database(lab.database)["revision"] == "006b4_security_decisions"

    pre = verify_database(lab.database)
    upgraded = upgrade_lifecycle_existing(
        lab.database, tmp_path / "backups", confirmed=True,
    )
    assert upgraded["revision"] == LIFECYCLE_REVISION
    assert "-pre006b4-" in upgraded["backup"]
    migrated = verify_database(lab.database)
    assert migrated["revision"] == LIFECYCLE_REVISION
    assert all(
        migrated["row_counts"][key] == count
        for key, count in pre["row_counts"].items()
    )

    app = create_app(database_url=lab.database_url, api_key=KEY)
    with TestClient(app, raise_server_exceptions=False) as client:
        admin = persona(client, lab, "admin.demo")
        supervisor = persona(client, lab, "supervisor.demo")
        auditor = persona(client, lab, "auditor.demo")
        ana = persona(client, lab, "ana.demo")
        bruno = persona(client, lab, "bruno.demo")

        created = client.post(
            "/v1/admin/queues", headers=admin,
            json={"id": "qa-operations", "name": "Fila QA Operacional"},
        )
        assert created.status_code == 201, created.text
        assert created.json()["audit"] == "APPLIED"
        overview = client.get("/v1/admin/overview", headers=admin)
        assert overview.status_code == 200
        queue = next(q for q in overview.json()["queues"] if q["id"] == "qa-operations")
        assert queue["lifecycle_state"] == "DRAFT"
        assert queue["lifecycle_version"] == 1
        for person in (supervisor, auditor, ana, bruno):
            assert client.patch(
                "/v1/admin/queues/qa-operations/state", headers=person,
                json={"state": "ACTIVE", "expected_version": 1},
            ).status_code == 403
        assert client.post(
            "/v1/handoffs",
            headers={**CLIENT_HEADERS, "Idempotency-Key": "qa-draft-deny"},
            json={
                "queue_id": "qa-operations",
                "external_conversation_id": "qa-draft-deny",
                "requester_label": "Solicitante sintético",
                "subject": "Fila em rascunho",
            },
        ).status_code == 409

        states = (
            ("ACTIVE", 1, 2),
            ("PAUSED", 2, 3),
            ("ACTIVE", 3, 4),
            ("PAUSED", 4, 5),
            ("ARCHIVED", 5, 6),
        )
        for state, version, result_version in states:
            change = client.patch(
                "/v1/admin/queues/qa-operations/state", headers=admin,
                json={"state": state, "expected_version": version},
            )
            assert change.status_code == 200, change.text
            assert change.json()["version"] == result_version
        assert client.patch(
            "/v1/admin/queues/qa-operations/state", headers=admin,
            json={"state": "ACTIVE", "expected_version": 6},
        ).status_code == 409

        intake = client.post(
            "/v1/handoffs",
            headers={**CLIENT_HEADERS, "Idempotency-Key": "qa-operations-handoff"},
            json={
                "queue_id": "n1",
                "external_conversation_id": "qa-operations-conversation",
                "requester_label": "Solicitante sintético",
                "subject": "QA transferência N1 para N2",
            },
        )
        assert intake.status_code == 201, intake.text
        sid = intake.json()["id"]
        first_message = client.post(
            f"/v1/handoffs/{sid}/messages", headers=CLIENT_HEADERS,
            json={
                "sender": "USER",
                "content": "Solicitação sintética restrita à fila N1",
                "external_message_id": "qa-n1-user",
            },
        )
        assert first_message.status_code == 201, first_message.text

        offer = client.post(
            "/v1/dispatch/offer", headers=CLIENT_HEADERS,
            json={"queue_id": "n1", "operation_id": "demo"},
        )
        assert offer.status_code == 200
        assert offer.json()["result"] == "offered"
        assert offer.json()["offer"]["operator_id"] == "op-ana"
        assert client.post(
            f"/v1/handoffs/{sid}/accept", headers=ana,
            json={"operator_id": "op-ana"},
        ).status_code == 200
        answer = client.post(
            f"/v1/handoffs/{sid}/messages", headers=ana,
            json={
                "sender": "OPERATOR", "operator_id": "op-ana",
                "content": "Atendimento N1 sintético",
                "external_message_id": "qa-n1-operator",
            },
        )
        assert answer.status_code == 201, answer.text

        internal = "Nota técnica interna N1->N2. " * 8
        transfer = client.post(
            f"/v1/handoffs/{sid}/transfer", headers=ana,
            json={"operator_id": "op-ana", "queue_id": "n2",
                  "reason": internal},
        )
        assert transfer.status_code == 200, transfer.text
        assert transfer.json()["queue_id"] == "n2"
        assert transfer.json()["status"] == "QUEUED"
        assert client.get(
            f"/v1/handoffs/{sid}/transfer-targets", headers=ana,
        ).status_code == 403

        next_offer = client.post(
            "/v1/dispatch/offer", headers=CLIENT_HEADERS,
            json={"queue_id": "n2", "operation_id": "demo"},
        )
        assert next_offer.status_code == 200
        assert next_offer.json()["result"] == "offered"
        assert next_offer.json()["offer"]["operator_id"] == "op-bruno"
        timeline = client.get(f"/v1/handoffs/{sid}/timeline", headers=bruno)
        assert timeline.status_code == 200
        assert timeline.json()["transfers"][-1]["reason"] == internal
        assert client.post(
            f"/v1/handoffs/{sid}/accept", headers=bruno,
            json={"operator_id": "op-bruno"},
        ).status_code == 200
        n2_message = client.post(
            f"/v1/handoffs/{sid}/messages", headers=CLIENT_HEADERS,
            json={
                "sender": "USER", "content": "Atualização sintética N2",
                "external_message_id": "qa-n2-user",
            },
        )
        assert n2_message.status_code == 201

        n1 = client.get(
            f"/v1/handoffs/{sid}/verified-history",
            params={"queue_id": "n1"}, headers=auditor,
        )
        n2 = client.get(
            f"/v1/handoffs/{sid}/verified-history",
            params={"queue_id": "n2"}, headers=supervisor,
        )
        assert n1.status_code == 200, n1.text
        assert n2.status_code == 200, n2.text
        assert "Solicitação sintética restrita à fila N1" in n1.text
        assert "Atualização sintética N2" not in n1.text
        assert "Atualização sintética N2" in n2.text
        assert "Atendimento N1 sintético" not in n2.text
        assert internal not in n1.text
        assert internal not in n2.text
        assert client.get(
            f"/v1/handoffs/{sid}/verified-history",
            params={"queue_id": "n2"}, headers=auditor,
        ).status_code == 404
        assert client.get(
            f"/v1/handoffs/{sid}/verified-history",
            params={"queue_id": "n1"}, headers=admin,
        ).status_code == 403

        closed = client.post(
            f"/v1/operators/op-bruno/handoffs/{sid}/close", headers=bruno,
        )
        assert closed.status_code == 200, closed.text
        assert closed.json()["status"] == "CLOSED"

    with sqlite3.connect(lab.database.as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute(
            "SELECT state, version FROM queue_lifecycle WHERE queue_id='qa-operations'",
        ).fetchone() == ("ARCHIVED", 6)
        events = db.execute(
            "SELECT to_state FROM queue_lifecycle_events "
            "WHERE queue_id='qa-operations' ORDER BY version",
        ).fetchall()
        assert [item[0] for item in events] == [
            "DRAFT", "ACTIVE", "PAUSED", "ACTIVE", "PAUSED", "ARCHIVED",
        ]
        assert db.execute(
            "SELECT count(*) FROM security_decisions WHERE "
            "queue_id='qa-operations' AND action='QUEUE_CREATED' AND outcome='APPLIED'",
        ).fetchone()[0] == 1
        assert db.execute(
            "SELECT status FROM handoff_sessions WHERE id=?", (sid,),
        ).fetchone()[0] == "CLOSED"
        assert db.execute(
            "SELECT count(*) FROM session_queue_segments WHERE session_id=?", (sid,),
        ).fetchone()[0] == 2
        assert db.execute(
            "SELECT count(*) FROM history_access_audit "
            "WHERE resource IN ('LIST','DETAIL')",
        ).fetchone()[0] >= 2

    assert verify_database(lab.database)["integrity"] == "ok"
