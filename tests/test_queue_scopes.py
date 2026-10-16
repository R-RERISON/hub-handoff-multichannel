"""SPEC-006A queue scoping/IDOR regression tests.

No corporate data or external connector required.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.auto_dispatch import run_dispatch_cycle
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    Operation,
    Queue,
    QueueRoleGrant,
    SessionTransfer,
    make_session_factory,
)
from handoff_hub.seed_demo_auth import provision


def setup(tmp_path):
    url = f"sqlite:///{tmp_path / 'scoping.sqlite'}"
    factory, engine = make_session_factory(url)
    credentials = tmp_path / "credentials.txt"
    provision(factory, credentials)
    passwords = {
        line.split(" [", 1)[0]: line.split("]: ", 1)[1]
        for line in credentials.read_text(encoding="utf-8").splitlines()
        if " [" in line and "]: " in line
    }
    engine.dispose()
    return create_app(database_url=url), factory, passwords


def login(client, passwords, username):
    r = client.post("/v1/auth/login", json={
        "username": username, "password": passwords[username]
    })
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


def ticket(client, headers, suffix, queue="n1"):
    return client.post("/v1/handoffs",
        headers={**headers, "Idempotency-Key": f"scoped-request-{suffix}"},
        json={
            "integration_id": "demo-bot", "operation_id": "demo",
            "queue_id": queue, "external_conversation_id": f"scoped-{suffix}",
            "requester_label": f"Solicitante {suffix}", "subject": "Teste RBAC",
        })


def test_auditor_only_sees_own_queue_and_admin_can_revoke(tmp_path):
    app, factory, passwords = setup(tmp_path)
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        auditor = login(c, passwords, "auditor.demo")
        n1 = ticket(c, admin, "n1", "n1")
        n2 = ticket(c, admin, "n2", "n2")
        assert n1.status_code == 201 and n2.status_code == 201
        dashboard = c.get("/v1/dashboard", headers=auditor).json()
        assert {q["id"] for q in dashboard["queues"]} == {"n1"}
        assert {h["id"] for h in dashboard["handoffs"]} == {n1.json()["id"]}
        assert {q["id"] for q in c.get("/v1/queues", headers=auditor).json()} == {"n1"}
        assert c.get(f"/v1/handoffs/{n2.json()['id']}/messages",
                     headers=auditor).status_code == 404
        assert c.get("/v1/queues/n2/rotation", headers=auditor).status_code == 404
        assert c.get("/v1/outbox", headers=auditor).status_code == 403
        with factory() as db:
            user = db.scalar(select(AuthUser).where(
                AuthUser.username == "auditor.demo"
            ))
            uid = user.id
        r = c.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n1", "role": "AUDITOR", "enabled": False,
        })
        assert r.status_code == 200, r.text
        assert c.get("/v1/me/queues", headers=auditor).json() == []
        assert c.get(f"/v1/handoffs/{n1.json()['id']}/messages",
                     headers=auditor).status_code == 404
        with factory() as db:
            assert db.get(QueueRoleGrant, (uid, "n1", "AUDITOR")) is None


def test_supervisor_grant_controls_queue_mutations(tmp_path):
    app, factory, passwords = setup(tmp_path)
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        supervisor = login(c, passwords, "supervisor.demo")
        with factory() as db:
            user = db.scalar(select(AuthUser).where(
                AuthUser.username == "supervisor.demo"
            ))
            uid = user.id
        revoke = c.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n2",
            "role": "SUPERVISOR", "enabled": False,
        })
        assert revoke.status_code == 200
        assert c.patch("/v1/queues/n2/members/op-ana", headers=supervisor,
                       json={"enabled": True}).status_code == 404
        assert c.get("/v1/queues/n2/rotation", headers=supervisor).status_code == 404
        assert c.patch("/v1/queues/n1/members/op-bruno", headers=supervisor,
                       json={"enabled": True}).status_code == 200
        assert c.patch("/v1/operators/op-ana/capacity", headers=supervisor,
                       json={"capacity": 2}).status_code == 200
        assert c.patch("/v1/operators/op-bruno/capacity", headers=supervisor,
                       json={"capacity": 2}).status_code == 403
        assert ticket(c, supervisor, "attempt-n2", "n2").status_code == 404
        assert ticket(c, supervisor, "allowed-n1", "n1").status_code == 201
        assert c.patch("/v1/admin/queue-grants", headers=supervisor, json={
            "user_id": uid, "queue_id": "n2", "role": "SUPERVISOR",
            "enabled": True,
        }).status_code == 403


def test_roles_cannot_cross_operations_using_queue_grants(tmp_path):
    app, _, passwords = setup(tmp_path)
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        auditor = login(c, passwords, "auditor.demo")
        assert c.get("/v1/queues/missing/rotation", headers=auditor).status_code == 404
        assert c.get("/v1/me/queues", headers=admin).status_code == 200
        assert c.get("/v1/me/queues", headers=auditor).status_code == 200


def test_transferred_conversation_does_not_leak_full_history(tmp_path):
    """Until segments exist, deny full transcript to scoped human viewers."""
    app, factory, passwords = setup(tmp_path)
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        supervisor = login(c, passwords, "supervisor.demo")
        handoff = ticket(c, admin, "transfer-guard", "n2")
        assert handoff.status_code == 201
        hid = handoff.json()["id"]
        with factory.begin() as db:
            db.add(SessionTransfer(
                session_id=hid, from_queue_id="n1", to_queue_id="n2",
                from_operator_id="op-ana", reason="Escalonamento técnico"
            ))
        assert c.get(f"/v1/handoffs/{hid}/messages",
                     headers=supervisor).status_code == 403
        assert c.get(f"/v1/handoffs/{hid}/timeline",
                     headers=supervisor).status_code == 403
        listed = c.get("/v1/handoffs", headers=supervisor).json()
        assert all(h["id"] != hid for h in listed)
        dashboard = c.get("/v1/dashboard", headers=supervisor).json()
        assert all(h["id"] != hid for h in dashboard["handoffs"])
        assert c.get(f"/v1/handoffs/{hid}/messages", headers=admin).status_code == 200


def test_scoped_operator_counts_do_not_include_other_queues(tmp_path):
    app, factory, passwords = setup(tmp_path)
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        supervisor = login(c, passwords, "supervisor.demo")
        with factory() as db:
            uid = db.scalar(select(AuthUser).where(
                AuthUser.username == "supervisor.demo"
            )).id
        r = c.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n2",
            "role": "SUPERVISOR", "enabled": False,
        })
        assert r.status_code == 200
        n2 = ticket(c, admin, "hidden-queue", "n2")
        assert n2.status_code == 201
        with factory.begin() as db:
            from handoff_hub.poc_db import HandoffSession
            row = db.get(HandoffSession, n2.json()["id"])
            row.operator_id = "op-bruno"
            row.status = "ACTIVE"
        dash = c.get("/v1/dashboard", headers=supervisor).json()
        assert {o["id"] for o in dash["operators"]} == {"op-ana"}
        assert all(q["id"] != "n2" for q in dash["queues"])
        assert all(h["id"] != n2.json()["id"] for h in dash["handoffs"])


def test_operator_can_transfer_to_n2_without_being_member_of_n2(tmp_path):
    """Dispatch membership is NOT destination authorization."""
    app, factory, passwords = setup(tmp_path)
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        ana = login(c, passwords, "ana.demo")
        bruno = login(c, passwords, "bruno.demo")
        supervisor = login(c, passwords, "supervisor.demo")
        auditor = login(c, passwords, "auditor.demo")
        handoff = ticket(c, admin, "operator-transfer-targets", "n1")
        assert handoff.status_code == 201
        hid = handoff.json()["id"]
        with factory.begin() as db:
            session = db.get(HandoffSession, hid)
            session.status = "ACTIVE"
            session.operator_id = "op-ana"

        assert {q["id"] for q in c.get("/v1/queues", headers=ana).json()} == {"n1"}
        discovered = c.get(f"/v1/handoffs/{hid}/transfer-targets", headers=ana)
        assert discovered.status_code == 200, discovered.text
        assert discovered.json()["source_queue_id"] == "n1"
        assert discovered.json()["destinations"] == [{"id": "n2", "name": "Suporte N2"}]

        for unauthorized in (bruno, auditor, supervisor, admin):
            response = c.get(f"/v1/handoffs/{hid}/transfer-targets",
                             headers=unauthorized)
            assert response.status_code == 403, response.text

        same_queue = c.post(f"/v1/handoffs/{hid}/transfer", headers=ana, json={
            "operator_id": "op-ana", "queue_id": "n1", "reason": "Nao permite auto-transferir"
        })
        assert same_queue.status_code == 422

        transferred = c.post(f"/v1/handoffs/{hid}/transfer", headers=ana, json={
            "operator_id": "op-ana", "queue_id": "n2", "reason": "Escalonamento para N2"
        })
        assert transferred.status_code == 200, transferred.text
        assert transferred.json()["queue_id"] == "n2"
        assert transferred.json()["operator_id"] is None
        assert transferred.json()["status"] == "QUEUED"

        inactive = c.get(f"/v1/handoffs/{hid}/transfer-targets", headers=ana)
        assert inactive.status_code == 403

        # Bruno can read the private handoff reason as soon as N2 offers him
        # the session, before he has accepted the transfer.
        run_dispatch_cycle(factory)
        offered = c.get(f"/v1/handoffs/{hid}/timeline", headers=bruno)
        assert offered.status_code == 200, offered.text
        transfer_note = offered.json()["transfers"][-1]
        assert transfer_note["reason"] == "Escalonamento para N2"
        assert transfer_note["from_operator_name"] == "Ana (demonstração)"
        assert transfer_note["from_queue_name"] == "Suporte N1"
        assert transfer_note["to_queue_name"] == "Suporte N2"


def test_transfer_destinations_do_not_expose_other_operations(tmp_path):
    app, factory, passwords = setup(tmp_path)
    with factory.begin() as db:
        db.add(Operation(id="other-operation", name="Outra operação"))
        db.flush()
        db.add(Queue(id="external-queue", operation_id="other-operation",
                     name="Fila de outra operação"))
    with TestClient(app) as c:
        admin = login(c, passwords, "admin.demo")
        ana = login(c, passwords, "ana.demo")
        handoff = ticket(c, admin, "transfer-operation-scope", "n1")
        assert handoff.status_code == 201
        hid = handoff.json()["id"]
        with factory.begin() as db:
            session = db.get(HandoffSession, hid)
            session.status = "ACTIVE"
            session.operator_id = "op-ana"
        response = c.get(f"/v1/handoffs/{hid}/transfer-targets", headers=ana)
        assert response.status_code == 200
        assert {q["id"] for q in response.json()["destinations"]} == {"n2"}
        forbidden = c.post(f"/v1/handoffs/{hid}/transfer", headers=ana, json={
            "operator_id": "op-ana", "queue_id": "external-queue",
            "reason": "Destino de outra operação"
        })
        assert forbidden.status_code == 422
        assert c.get("/v1/queues", headers=ana).json()[0]["id"] == "n1"
