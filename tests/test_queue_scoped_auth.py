"""SPEC-006A security gates: scoped queues, live grants and cross-queue denial."""
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, QueueRoleGrant, make_session_factory
from handoff_hub.seed_demo_auth import provision

KEY = {"X-POC-Key": "legacy-test-key"}


def context(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'scoped.db'}"
    factory, engine = make_session_factory(url)
    credentials = tmp_path / "credentials.txt"
    provision(factory, credentials)
    engine.dispose()
    secrets = {
        line.split(" [", 1)[0]: line.split("]: ", 1)[1]
        for line in credentials.read_text(encoding="utf-8").splitlines()
        if " [" in line and "]: " in line
    }
    return create_app(database_url=url, api_key="legacy-test-key"), factory, secrets


def bearer(client: TestClient, username: str, secrets: dict) -> dict:
    response = client.post("/v1/auth/login", json={
        "username": username, "password": secrets[username],
    })
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


def ticket(client: TestClient, n: int, queue_id: str):
    response = client.post(
        "/v1/handoffs",
        headers={**KEY, "Idempotency-Key": f"scoped-idempotency-{n}"},
        json={"requester_label": f"Request {n}", "subject": "Scoped test",
              "external_conversation_id": f"conv-{n}", "queue_id": queue_id},
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def test_grants_restrict_queue_lists_metrics_mutations_and_chat(tmp_path):
    app, factory, secrets = context(tmp_path)
    with TestClient(app) as client:
        administrator = bearer(client, "admin.demo", secrets)
        supervisor = bearer(client, "supervisor.demo", secrets)
        auditor = bearer(client, "auditor.demo", secrets)
        n1_id = ticket(client, 1, "n1")
        n2_id = ticket(client, 2, "n2")

        assert client.get("/v1/dashboard", headers=supervisor).status_code == 200
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == "supervisor.demo"))
            grant = db.get(QueueRoleGrant, (user.id, "n2", "SUPERVISOR"))
            assert grant is not None
            user_id = user.id

        revoked = client.delete(
            f"/v1/admin/queue-grants/{user_id}/n2/SUPERVISOR",
            headers=administrator,
        )
        assert revoked.status_code == 200
        # Existing bearer session sees revocation immediately.
        queues = client.get("/v1/queues", headers=supervisor)
        assert queues.status_code == 200
        assert [q["id"] for q in queues.json()] == ["n1"]
        dashboard = client.get("/v1/dashboard", headers=supervisor)
        assert dashboard.status_code == 200
        assert {q["id"] for q in dashboard.json()["queues"]} == {"n1"}
        assert {h["id"] for h in dashboard.json()["handoffs"]} == {n1_id}
        handoffs = client.get("/v1/handoffs", headers=supervisor)
        assert {h["id"] for h in handoffs.json()} == {n1_id}
        assert client.get("/v1/queues/n2/rotation", headers=supervisor).status_code == 404
        assert client.patch(
            "/v1/queues/n2/members/op-ana",
            headers=supervisor, json={"enabled": True},
        ).status_code == 404
        assert client.patch(
            "/v1/operators/op-bruno/capacity",
            headers=supervisor, json={"capacity": 3},
        ).status_code == 403
        assert client.get(
            f"/v1/handoffs/{n2_id}/messages", headers=supervisor
        ).status_code == 404
        assert client.get("/v1/outbox", headers=auditor).status_code == 403
        assert client.get("/v1/outbox", headers=administrator).status_code == 403

        new_grant = client.post("/v1/admin/queue-grants", headers=administrator, json={
            "user_id": user_id, "queue_id": "n2", "role": "SUPERVISOR",
        })
        assert new_grant.status_code == 201
        assert {q["id"] for q in client.get(
            "/v1/queues", headers=supervisor
        ).json()} == {"n1", "n2"}


def test_auditor_only_sees_assigned_queues_and_no_cross_queue_timeline(tmp_path):
    app, factory, secrets = context(tmp_path)
    with TestClient(app) as client:
        admin = bearer(client, "admin.demo", secrets)
        auditor = bearer(client, "auditor.demo", secrets)
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == "auditor.demo"))
            auditor_id = user.id
        assert client.delete(
            f"/v1/admin/queue-grants/{auditor_id}/n2/AUDITOR",
            headers=admin,
        ).status_code == 200
        n1_id = ticket(client, 11, "n1")
        n2_id = ticket(client, 12, "n2")
        assert {h["id"] for h in client.get(
            "/v1/handoffs", headers=auditor
        ).json()} == {n1_id}
        assert client.get(
            f"/v1/handoffs/{n2_id}/messages", headers=auditor
        ).status_code == 404
        assert client.get(
            f"/v1/handoffs/{n2_id}/timeline", headers=auditor
        ).status_code == 404
        assert client.get("/v1/queues/n2/rotation", headers=auditor).status_code == 404
        assert client.post("/v1/admin/queue-grants", headers=auditor, json={
            "user_id": auditor_id, "queue_id": "n2", "role": "AUDITOR",
        }).status_code == 403
        # Re-provisioning demo accounts must not silently restore revoked grants.
        provision(factory, tmp_path / "credentials.txt")
        assert [q["id"] for q in client.get(
            "/v1/me/queues", headers=auditor
        ).json()] == ["n1"]


def test_transferred_conversation_is_fail_closed_without_all_queue_grants(tmp_path):
    app, factory, secrets = context(tmp_path)
    with TestClient(app) as client:
        admin = bearer(client, "admin.demo", secrets)
        auditor = bearer(client, "auditor.demo", secrets)
        handoff_id = ticket(client, 40, "n1")
        assigned = client.post("/v1/dispatch/next", headers=KEY,
                               json={"operation_id": "demo", "queue_id": "n1"})
        assert assigned.status_code == 200
        transferred = client.post(
            f"/v1/handoffs/{handoff_id}/transfer", headers=KEY,
            json={"operator_id": "op-ana", "queue_id": "n2", "reason": "N2 needed"},
        )
        assert transferred.status_code == 200
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == "auditor.demo"))
            auditor_id = user.id
        assert client.delete(
            f"/v1/admin/queue-grants/{auditor_id}/n1/AUDITOR",
            headers=admin,
        ).status_code == 200
        assert client.get(
            f"/v1/handoffs/{handoff_id}/messages", headers=auditor
        ).status_code == 404
        assert client.get(
            f"/v1/handoffs/{handoff_id}/timeline", headers=auditor
        ).status_code == 404
        restored = client.post(
            "/v1/admin/queue-grants", headers=admin,
            json={"user_id": auditor_id, "queue_id": "n1", "role": "AUDITOR"},
        )
        assert restored.status_code == 201
        assert client.get(
            f"/v1/handoffs/{handoff_id}/timeline", headers=auditor
        ).status_code == 200


def test_operator_transfer_catalog_does_not_expose_other_queue_load(tmp_path):
    app, _, secrets = context(tmp_path)
    with TestClient(app) as client:
        ana = bearer(client, "ana.demo", secrets)
        ticket(client, 90, "n2")
        result = client.get("/v1/queues", headers=ana)
        assert result.status_code == 200
        assert {q["id"] for q in result.json()} == {"n1", "n2"}
        assert all(q["waiting"] == 0 for q in result.json())
        assert client.get("/v1/queues/n2/rotation", headers=ana).status_code == 403
        assert client.get("/v1/dashboard", headers=ana).status_code == 403
