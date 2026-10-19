"""SPEC-007/A0: admin-only inventory and cross-operation isolation, TEMP only."""
from __future__ import annotations

import sqlite3

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, Operation, Queue, make_session_factory
from scripts import lab_environment
from scripts.release_grant_toggle import bearer


def prepare(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def account_id(database_url, username):
    factory, engine = make_session_factory(database_url)
    try:
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == username))
            assert user is not None
            return user.id
    finally:
        engine.dispose()


def test_admin_inventory_requires_bearer_and_admin_role(tmp_path, monkeypatch):
    lab = prepare(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="qa-admin-inventory-only")
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/v1/admin/overview").status_code == 401
        for username in ("supervisor.demo", "auditor.demo", "ana.demo"):
            header = bearer(client, lab.credentials, username,
                            account_id(lab.database_url, username))
            denied = client.get("/v1/admin/overview", headers=header)
            assert denied.status_code == 403
            assert "queues" not in denied.text
            assert "password" not in denied.text


def test_admin_inventory_is_read_only_and_scoped_to_operation(tmp_path, monkeypatch):
    lab = prepare(tmp_path, monkeypatch)
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory.begin() as db:
            db.add(Operation(id="other-op", name="OUTSIDE_OPERATION_SECRET"))
            db.add(Queue(id="foreign-queue", operation_id="other-op",
                         name="OUTSIDE_QUEUE_SECRET"))
    finally:
        engine.dispose()
    app = create_app(database_url=lab.database_url, api_key="qa-admin-inventory-only")
    with TestClient(app, raise_server_exceptions=False) as client:
        header = bearer(client, lab.credentials, "admin.demo",
                        account_id(lab.database_url, "admin.demo"))
        response = client.get("/v1/admin/overview", headers=header)
        assert response.status_code == 200
        payload = response.json()
        assert payload["operation"]["id"] == "demo"
        assert payload["summary"]["queues"] == 2
        assert payload["summary"]["operators"] == 2
        assert payload["summary"]["accounts"] == 5
        assert payload["summary"]["role_grants"] == 3
        assert {q["id"] for q in payload["queues"]} == {"n1", "n2"}
        assert payload["capabilities"] == {
            "read_only": True,
            "queue_lifecycle_available": False,
            "identity_provider": "LOCAL_POC",
        }
        assert "OUTSIDE_OPERATION_SECRET" not in response.text
        assert "OUTSIDE_QUEUE_SECRET" not in response.text
        for forbidden in ("password_hash", "access_token", "message_content",
                          "external_conversation_id"):
            assert forbidden not in response.text
        # Read-only projection cannot insert sessions or grant membership.
        with sqlite3.connect(lab.database.as_uri() + "?mode=ro", uri=True) as db:
            assert db.execute("SELECT count(*) FROM handoff_sessions").fetchone()[0] == 0


def test_no_administration_writes_exposed_by_inventory_endpoint(tmp_path, monkeypatch):
    lab = prepare(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="qa-admin-inventory-only")
    with TestClient(app, raise_server_exceptions=False) as client:
        header = bearer(client, lab.credentials, "admin.demo",
                        account_id(lab.database_url, "admin.demo"))
        assert client.post("/v1/admin/overview", headers=header).status_code == 405
        assert client.patch("/v1/admin/overview", headers=header).status_code == 405
