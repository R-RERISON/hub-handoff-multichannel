"""SPEC-006A queue scoping/IDOR regression tests.

No corporate data or external connector required.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, QueueRoleGrant, SessionTransfer, make_session_factory
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
