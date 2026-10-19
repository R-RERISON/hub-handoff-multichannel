"""SPEC-007/A1.1 — transactional admin queue creation on disposable SQLite."""
from __future__ import annotations

import sqlite3
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    AuthUser,
    Operation,
    Queue,
    QueueMembership,
    QueueRoleGrant,
    make_session_factory,
)
from handoff_hub.seed_demo_auth import provision
from scripts import lab_environment
from scripts.release_grant_toggle import bearer


def prepared(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def account_id(url, username):
    factory, engine = make_session_factory(url)
    try:
        with factory() as db:
            user = db.scalar(select(AuthUser).where(AuthUser.username == username))
            assert user is not None
            return user.id
    finally:
        engine.dispose()


def login(client, lab, name):
    return bearer(client, lab.credentials, name, account_id(lab.database_url, name))


def counts(lab, queue_id):
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            return (
                db.scalar(select(func.count()).select_from(Queue)
                          .where(Queue.id == queue_id)),
                db.scalar(select(func.count()).select_from(QueueMembership)
                          .where(QueueMembership.queue_id == queue_id)),
                db.scalar(select(func.count()).select_from(QueueRoleGrant)
                          .where(QueueRoleGrant.queue_id == queue_id)),
            )
    finally:
        engine.dispose()


def journal_count(db_path, queue_id):
    with sqlite3.connect(db_path.as_uri() + "?mode=ro", uri=True) as db:
        return db.execute(
            "SELECT count(*) FROM security_decisions "
            "WHERE queue_id=? AND action='QUEUE_CREATED' AND outcome='APPLIED'",
            (queue_id,),
        ).fetchone()[0]


def test_admin_only_and_anonymous_cannot_create(tmp_path, monkeypatch):
    lab = prepared(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="a1-lab-only")
    body = {"id": "n3", "name": "Suporte N3"}
    with TestClient(app, raise_server_exceptions=False) as c:
        assert c.post("/v1/admin/queues", json=body).status_code == 401
        for username in ("supervisor.demo", "auditor.demo",
                         "ana.demo", "bruno.demo"):
            denial = c.post("/v1/admin/queues", json=body,
                            headers=login(c, lab, username))
            assert denial.status_code == 403
        assert counts(lab, "n3") == (0, 0, 0)
        assert journal_count(lab.database, "n3") == 0


def test_admin_create_is_scoped_audited_and_does_not_grant_access(tmp_path, monkeypatch):
    lab = prepared(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="a1-lab-only")
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        result = c.post("/v1/admin/queues", headers=admin,
                        json={"id": "n3", "name": "Suporte N3"})
        assert result.status_code == 201, result.text
        assert result.json() == {
            "id": "n3", "name": "Suporte N3",
            "operation_id": "demo", "audit": "APPLIED",
        }
        assert counts(lab, "n3") == (1, 0, 0)
        assert journal_count(lab.database, "n3") == 1
        overview = c.get("/v1/admin/overview", headers=admin)
        assert overview.status_code == 200
        assert overview.json()["summary"]["queues"] == 3
        assert {q["id"] for q in overview.json()["queues"]} == {"n1", "n2", "n3"}
        auditor = login(c, lab, "auditor.demo")
        assert "n3" not in [q["id"] for q in
                            c.get("/v1/me/queues", headers=auditor).json()]


def test_duplicate_and_foreign_operation_queue_id_fail_closed(tmp_path, monkeypatch):
    lab = prepared(tmp_path, monkeypatch)
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory.begin() as db:
            db.add(Operation(id="other-op", name="Operacao isolada"))
            db.add(Queue(id="other-id", operation_id="other-op", name="Sigilo"))
    finally:
        engine.dispose()
    app = create_app(database_url=lab.database_url, api_key="a1-lab-only")
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        other = c.post("/v1/admin/queues", headers=admin,
                       json={"id": "other-id", "name": "Colisao"})
        assert other.status_code == 409
        assert "Sigilo" not in other.text
        assert journal_count(lab.database, "other-id") == 0
        first = c.post("/v1/admin/queues", headers=admin,
                       json={"id": "novo-queue", "name": "Fila nova"})
        second = c.post("/v1/admin/queues", headers=admin,
                        json={"id": "novo-queue", "name": "Fila nova"})
        assert first.status_code == 201
        assert second.status_code == 409
        assert counts(lab, "novo-queue") == (1, 0, 0)
        assert journal_count(lab.database, "novo-queue") == 1


def test_invalid_id_and_name_never_mutate(tmp_path, monkeypatch):
    lab = prepared(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="a1-lab-only")
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        bad_values = (
            {"id": "bad/queue", "name": "Fila"},
            {"id": "N3", "name": "Fila"},
            {"id": "n3", "name": " Abc"},
            {"id": "n3", "name": "ABC\nDEF"},
            {"id": "n3", "name": "ab"},
        )
        for body in bad_values:
            response = c.post("/v1/admin/queues", headers=admin, json=body)
            assert response.status_code == 422, body
        assert counts(lab, "n3") == (0, 0, 0)
        assert journal_count(lab.database, "n3") == 0


def test_journal_failure_rolls_back_new_queue(tmp_path, monkeypatch):
    lab = prepared(tmp_path, monkeypatch)
    with sqlite3.connect(lab.database) as db:
        db.execute(
            "CREATE TRIGGER spec007_deny_audit BEFORE INSERT ON security_decisions "
            "WHEN NEW.action='QUEUE_CREATED' BEGIN "
            "SELECT RAISE(ABORT,'qa simulated outage'); END"
        )
    app = create_app(database_url=lab.database_url, api_key="a1-lab-only")
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        failed = c.post("/v1/admin/queues", headers=admin,
                        json={"id": "n3", "name": "Suporte N3"})
        assert failed.status_code == 503
        assert counts(lab, "n3") == (0, 0, 0)
        assert journal_count(lab.database, "n3") == 0


def test_unversioned_poc_refuses_mutation_without_audit(tmp_path):
    database = tmp_path / "legacy-local.db"
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    credentials = tmp_path / "qa-credentials.txt"
    try:
        provision(factory, credentials)
    finally:
        engine.dispose()
    app = create_app(database_url=f"sqlite:///{database.as_posix()}",
                     api_key="a1-lab-only")
    with TestClient(app, raise_server_exceptions=False) as c:
        header = bearer(c, credentials, "admin.demo",
                        account_id(f"sqlite:///{database.as_posix()}", "admin.demo"))
        outcome = c.post("/v1/admin/queues", headers=header,
                         json={"id": "n3", "name": "Suporte N3"})
        assert outcome.status_code == 503
    with sqlite3.connect(database) as db:
        assert db.execute(
            "SELECT count(*) FROM queues WHERE id='n3'"
        ).fetchone()[0] == 0
        assert db.execute(
            "SELECT name FROM sqlite_master WHERE name='security_decisions'"
        ).fetchone() is None


def test_competing_create_requests_produce_only_one_queue_and_audit(tmp_path, monkeypatch):
    lab = prepared(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="a1-lab-only")
    with TestClient(app, raise_server_exceptions=False) as c:
        admin = login(c, lab, "admin.demo")
        def create(_):
            return c.post("/v1/admin/queues", headers=admin,
                          json={"id": "n4", "name": "Suporte N4"}).status_code
        with ThreadPoolExecutor(max_workers=2) as executor:
            results = list(executor.map(create, range(2)))
        assert sorted(results) == [201, 409]
        assert counts(lab, "n4") == (1, 0, 0)
        assert journal_count(lab.database, "n4") == 1
