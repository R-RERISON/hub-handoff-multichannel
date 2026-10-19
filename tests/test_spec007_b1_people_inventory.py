"""SPEC-007/B1.0: read-only operation-scoped people directory (TEMP only)."""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    AuthUser,
    Operation,
    Operator,
    Queue,
    QueueMembership,
    make_session_factory,
)
from scripts import lab_environment
from scripts.release_grant_toggle import bearer


def setup_lab(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def login(client, lab, username):
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == username))
            assert user is not None
            user_id = user.id
    finally:
        engine.dispose()
    return bearer(client, lab.credentials, username, user_id)


def test_people_directory_requires_admin_and_bearer(tmp_path, monkeypatch):
    lab = setup_lab(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="b1-people-lab")
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/v1/admin/people").status_code == 401
        for username in ("supervisor.demo", "auditor.demo", "ana.demo"):
            response = client.get(
                "/v1/admin/people", headers=login(client, lab, username),
            )
            assert response.status_code == 403
            assert "operators" not in response.text


def test_people_directory_scopes_accounts_operators_and_memberships(
    tmp_path, monkeypatch,
):
    lab = setup_lab(tmp_path, monkeypatch)
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory.begin() as db:
            db.add(Operation(id="external-op", name="FOREIGN_OPERATION_PRIVATE"))
            db.add(Operator(
                id="external-operator", operation_id="external-op",
                name="FOREIGN_OPERATOR_PRIVATE", presence="AVAILABLE", capacity=2,
            ))
            db.add(Queue(
                id="external-queue", operation_id="external-op",
                name="FOREIGN_QUEUE_PRIVATE",
            ))
            db.flush()
            db.add(QueueMembership(
                operator_id="external-operator", queue_id="external-queue",
            ))
            db.add(AuthUser(
                id="external-account", username="FOREIGN_ACCOUNT_PRIVATE",
                password_hash="not-a-real-hash", role="AUDITOR",
                operation_id="external-op", is_active=True,
            ))
            # Within-operation operator without membership must remain visible.
            db.add(Operator(
                id="unassigned-op", operation_id="demo", name="Unassigned Demo",
                presence="OFFLINE", capacity=1,
            ))
    finally:
        engine.dispose()
    app = create_app(database_url=lab.database_url, api_key="b1-people-lab")
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/v1/admin/people", headers=login(client, lab, "admin.demo"),
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["operation"]["id"] == "demo"
        assert data["capabilities"] == {
            "read_only": True,
            "membership_write_available": False,
            "grant_write_available": False,
            "identity_provider": "LOCAL_POC",
        }
        ops = {operator["id"]: operator for operator in data["operators"]}
        assert set(ops) == {"op-ana", "op-bruno", "unassigned-op"}
        assert ops["unassigned-op"]["memberships"] == []
        assert ops["unassigned-op"]["active"] == 0
        assert all(
            {"id", "name", "presence", "capacity", "active", "offered", "memberships"}
            == set(operator) for operator in data["operators"]
        )
        assert len(data["accounts"]) == 5
        assert all(account["role"] in (
            "ADMIN", "SUPERVISOR", "AUDITOR", "OPERATOR",
        ) for account in data["accounts"])
        assert all(set(account) == {
            "id", "username", "role", "is_active", "operator_id",
        } for account in data["accounts"])
        for forbidden in (
            "FOREIGN_OPERATION_PRIVATE", "FOREIGN_OPERATOR_PRIVATE",
            "FOREIGN_QUEUE_PRIVATE", "FOREIGN_ACCOUNT_PRIVATE",
            "external-operator", "external-queue", "external-account",
            "password", "token_hash", "access_token",
            "requester_label", "external_conversation_id", "subject",
        ):
            assert forbidden not in response.text
        assert client.post("/v1/admin/people", headers=login(
            client, lab, "admin.demo",
        )).status_code == 405
        assert client.patch("/v1/admin/people", headers=login(
            client, lab, "admin.demo",
        )).status_code == 405
    # No write-side effects from directory reads.
    with sqlite3.connect(lab.database.as_uri() + "?mode=ro", uri=True) as db:
        assert db.execute("SELECT count(*) FROM handoff_sessions").fetchone()[0] == 0
        assert db.execute(
            "SELECT count(*) FROM queue_memberships WHERE queue_id='external-queue'"
        ).fetchone()[0] == 1


def test_membership_without_account_grant_is_not_authorization(
    tmp_path, monkeypatch,
):
    lab = setup_lab(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="b1-people-lab")
    with TestClient(app, raise_server_exceptions=False) as client:
        admin = login(client, lab, "admin.demo")
        before = client.get("/v1/admin/people", headers=admin)
        assert before.status_code == 200
        accounts = before.json()["accounts"]
        operators = before.json()["operators"]
        assert any(operator["memberships"] for operator in operators)
        assert all("grants" not in operator for operator in operators)
        assert all("grants" not in account for account in accounts)
        # A directory read does not grant an auditor mutation privileges.
        auditor = login(client, lab, "auditor.demo")
        denied = client.patch(
            "/v1/operators/op-ana/capacity", headers=auditor,
            json={"capacity": 2},
        )
        assert denied.status_code == 403
