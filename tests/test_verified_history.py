"""SPEC-006B-4.1: authenticated isolation for runtime-verified queue history.

All data is synthetic and every DB is created under tmp_path.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select, text, update

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    SessionEvent,
    make_session_factory,
)
from handoff_hub.provenance_schema import (
    MESSAGE_QUEUE_PROVENANCE,
    SESSION_EVENT_QUEUE_PROVENANCE,
    SESSION_QUEUE_SEGMENTS,
)
from handoff_hub.schema_admin import create_new
from handoff_hub.seed_demo_auth import provision

KEY = {"X-POC-Key": "local-test-only"}
BASE = "/v1/handoffs"


def environment(tmp_path, *, versioned=True):
    path = tmp_path / ("verified.db" if versioned else "original.db")
    if versioned:
        create_new(path, confirmed=True)
    url = f"sqlite:///{path.as_posix()}"
    factory, engine = make_session_factory(url)
    credentials = tmp_path / "credentials.txt"
    provision(factory, credentials)
    passwords = {
        line.split(" [", 1)[0]: line.split("]: ", 1)[1]
        for line in credentials.read_text(encoding="utf-8").splitlines()
        if " [" in line and "]: " in line
    }
    engine.dispose()
    return create_app(database_url=url, api_key="local-test-only"), factory, passwords


def bearer(client, passwords, name):
    response = client.post("/v1/auth/login", json={
        "username": name, "password": passwords[name],
    })
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def new_ticket(client, suffix):
    response = client.post(
        BASE, headers={**KEY, "Idempotency-Key": f"verified-{suffix}"},
        json={
            "operation_id": "demo",
            "integration_id": "demo-bot",
            "queue_id": "n1",
            "requester_label": "Pessoa sintética",
            "subject": "Teste segregado",
            "external_conversation_id": f"demo-{suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def user_message(client, hid, name):
    response = client.post(f"{BASE}/{hid}/messages", headers=KEY, json={
        "sender": "USER", "content": name, "external_message_id": f"ext-{name}",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def transfer(client, factory, hid):
    with factory.begin() as db:
        row = db.get(HandoffSession, hid)
        row.status = "ACTIVE"
        row.operator_id = "op-ana"
    response = client.post(f"{BASE}/{hid}/transfer", headers=KEY, json={
        "operator_id": "op-ana", "queue_id": "n2",
        "reason": "Nota interna secreta da transferência",
    })
    assert response.status_code == 200, response.text


def history(client, hid, queue, headers):
    return client.get(f"{BASE}/{hid}/verified-history", params={
        "queue_id": queue,
    }, headers=headers)


def test_scoped_n1_and_n2_receive_only_own_verified_history(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        admin = bearer(client, passwords, "admin.demo")
        ana = bearer(client, passwords, "ana.demo")
        hid = new_ticket(client, "two-queues")
        n1id = user_message(client, hid, "Mensagem somente N1")
        transfer(client, factory, hid)
        n2id = user_message(client, hid, "Mensagem somente N2")

        n1 = history(client, hid, "n1", auditor)
        assert n1.status_code == 200, n1.text
        assert n1.json()["scope"] == "RUNTIME_VERIFIED_QUEUE_ONLY"
        assert n1.json()["partial_history"] is True
        assert [m["id"] for m in n1.json()["messages"]] == [n1id]
        assert {e["type"] for e in n1.json()["events"]} == {"QUEUED", "TRANSFERRED"}
        assert "Nota interna secreta" not in n1.text
        assert "Mensagem somente N2" not in n1.text
        assert "n2" not in n1.text

        n2 = history(client, hid, "n2", supervisor)
        assert n2.status_code == 200, n2.text
        assert [m["id"] for m in n2.json()["messages"]] == [n2id]
        assert "Mensagem somente N1" not in n2.text
        assert "Nota interna secreta" not in n2.text

        assert history(client, hid, "n2", auditor).status_code == 404
        assert history(client, hid, "n1", admin).status_code == 403
        assert history(client, hid, "n1", ana).status_code == 403
        assert history(client, hid, "n1", {}).status_code == 401
        assert history(client, "not-a-handoff", "n1", auditor).status_code == 404
        # Full-history routes stay blocked for scoped users; operator flow unchanged.
        assert client.get(f"{BASE}/{hid}/messages", headers=supervisor).status_code == 403
        assert client.get(f"{BASE}/{hid}/timeline", headers=supervisor).status_code == 403
        assert client.get(f"{BASE}/{hid}/messages", headers=KEY).status_code == 200


def test_grant_revocation_is_effective_on_next_read(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        admin = bearer(client, passwords, "admin.demo")
        hid = new_ticket(client, "revocation")
        user_message(client, hid, "Conteúdo protegido")
        assert history(client, hid, "n1", auditor).status_code == 200
        with factory() as db:
            uid = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "auditor.demo",
            ))
        revoked = client.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n1",
            "role": "AUDITOR", "enabled": False,
        })
        assert revoked.status_code == 200, revoked.text
        assert history(client, hid, "n1", auditor).status_code == 404


def test_unverified_and_non_runtime_rows_never_appear(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "unverified")
        first = user_message(client, hid, "Aprovada")
        second = user_message(client, hid, "Sem confiança")
        third = user_message(client, hid, "Origem não runtime")
        with factory.begin() as db:
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == second)
                .values(confidence="UNDETERMINED")
            )
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == third)
                .values(assigned_by="MIGRATION")
            )
            queued = db.scalar(select(SessionEvent.id).where(
                SessionEvent.session_id == hid,
                SessionEvent.event_type == "QUEUED",
            ))
            db.execute(
                update(SESSION_EVENT_QUEUE_PROVENANCE)
                .where(SESSION_EVENT_QUEUE_PROVENANCE.c.event_id == queued)
                .values(confidence="UNDETERMINED")
            )
        result = history(client, hid, "n1", auditor)
        assert result.status_code == 200, result.text
        assert [m["id"] for m in result.json()["messages"]] == [first]
        assert result.json()["events"] == []


def test_invalid_cross_session_segment_reference_cannot_grant_access(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid1 = new_ticket(client, "first")
        m1 = user_message(client, hid1, "Compartimentada")
        hid2 = new_ticket(client, "second")
        m2 = user_message(client, hid2, "Segundo ticket")
        with factory.begin() as db:
            foreign_segment = db.scalar(select(SESSION_QUEUE_SEGMENTS.c.id).where(
                SESSION_QUEUE_SEGMENTS.c.session_id == hid2,
            ))
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == m1)
                .values(segment_id=foreign_segment)
            )
        result1 = history(client, hid1, "n1", auditor)
        result2 = history(client, hid2, "n1", auditor)
        assert result1.status_code == 200
        assert result1.json()["messages"] == []
        assert [m["id"] for m in result2.json()["messages"]] == [m2]


def test_original_unversioned_db_never_unlocks_history(tmp_path):
    app, factory, passwords = environment(tmp_path, versioned=False)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        hid = new_ticket(client, "old-db")
        user_message(client, hid, "Histórico POC")
        transfer(client, factory, hid)
        assert history(client, hid, "n1", auditor).status_code == 404
        assert client.get(f"{BASE}/{hid}/messages", headers=supervisor).status_code == 403
        assert client.get(f"{BASE}/{hid}/timeline", headers=supervisor).status_code == 403
    with factory() as db:
        tables = set(db.scalars(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).all())
        assert len(tables) == 17
        assert "session_queue_segments" not in tables
        assert "alembic_version" not in tables
