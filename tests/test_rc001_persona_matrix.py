"""Integrated RC-001 G02/G05 persona contract, synthetic 006b4 only."""
from __future__ import annotations

import sqlite3

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, make_session_factory
from scripts import lab_environment
from scripts.release_grant_toggle import bearer


@pytest.fixture
def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def identity(lab, username: str) -> str:
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            account = db.scalar(select(AuthUser).where(AuthUser.username == username))
            assert account is not None
            return account.id
    finally:
        engine.dispose()


def token(client, lab, username: str) -> dict[str, str]:
    return bearer(client, lab.credentials, username, identity(lab, username))


def test_persona_matrix_admin_and_operator_boundaries(lab):
    app = create_app(database_url=lab.database_url, api_key="qa-batch-only")
    with TestClient(app, raise_server_exceptions=False) as client:
        accounts = ("admin.demo", "supervisor.demo", "auditor.demo",
                    "ana.demo", "bruno.demo")
        auth = {name: token(client, lab, name) for name in accounts}
        for endpoint in ("/v1/admin/overview", "/v1/admin/people"):
            assert client.get(endpoint).status_code == 401
            for name in accounts:
                response = client.get(endpoint, headers=auth[name])
                assert response.status_code == (200 if name == "admin.demo" else 403)
                if name != "admin.demo":
                    for forbidden in ("password_hash", "access_token", "operator_id"):
                        assert forbidden not in response.text
                else:
                    assert "password_hash" not in response.text
                    assert "access_token" not in response.text
                    assert "token_hash" not in response.text

        for person, own, other in (
            ("ana.demo", "op-ana", "op-bruno"),
            ("bruno.demo", "op-bruno", "op-ana"),
        ):
            assert client.get(f"/v1/operators/{own}/work",
                              headers=auth[person]).status_code == 200
            assert client.get(f"/v1/operators/{other}/work",
                              headers=auth[person]).status_code == 403
            assert client.get(f"/v1/operators/{own}/work").status_code == 401

        history = "/v1/history/verified-sessions"
        assert client.get(history, params={"queue_id": "n1"}).status_code == 401
        assert client.get(history, params={"queue_id": "n1"},
                          headers=auth["auditor.demo"]).status_code == 200
        assert client.get(history, params={"queue_id": "n2"},
                          headers=auth["auditor.demo"]).status_code == 404
        for queue_id in ("n1", "n2"):
            assert client.get(history, params={"queue_id": queue_id},
                              headers=auth["supervisor.demo"]).status_code == 200
        for username in ("admin.demo", "ana.demo", "bruno.demo"):
            assert client.get(history, params={"queue_id": "n1"},
                              headers=auth[username]).status_code == 403


def test_revocation_and_non_admin_grant_mutation_fail_closed(lab):
    app = create_app(database_url=lab.database_url, api_key="qa-batch-only")
    with TestClient(app, raise_server_exceptions=False) as client:
        accounts = ("supervisor.demo", "auditor.demo", "ana.demo", "bruno.demo")
        auth = {name: token(client, lab, name) for name in accounts}
        target = identity(lab, "auditor.demo")
        patch = {"user_id": target, "queue_id": "n2",
                 "role": "AUDITOR", "enabled": True}

        with sqlite3.connect(lab.database.as_uri() + "?mode=ro", uri=True) as db:
            before = db.execute("SELECT count(*) FROM queue_role_grants").fetchone()[0]
        assert client.patch("/v1/admin/queue-grants", json=patch).status_code == 401
        for username in accounts:
            response = client.patch("/v1/admin/queue-grants",
                                    headers=auth[username], json=patch)
            assert response.status_code == 403
            assert "password_hash" not in response.text
        with sqlite3.connect(lab.database.as_uri() + "?mode=ro", uri=True) as db:
            assert db.execute("SELECT count(*) FROM queue_role_grants").fetchone()[0] == before
            assert db.execute(
                "SELECT count(*) FROM queue_role_grants "
                "WHERE user_id=? AND queue_id='n2' AND role='AUDITOR'",
                (target,),
            ).fetchone()[0] == 0

        auditor = auth["auditor.demo"]
        assert client.post("/v1/auth/logout", headers=auditor).status_code == 200
        for endpoint in (
            "/v1/auth/me", "/v1/me/queues",
            "/v1/history/verified-sessions?queue_id=n1",
            "/v1/admin/people",
        ):
            assert client.get(endpoint, headers=auditor).status_code == 401
