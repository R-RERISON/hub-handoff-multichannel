"""POC-005 gates: server RBAC, online lease, durable rotation, logout recovery."""
from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient
from handoff_hub.auto_dispatch import run_dispatch_cycle
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import HandoffSession, make_session_factory
from handoff_hub.seed_demo_auth import provision


def setup_poc(tmp_path: Path):
    url = "sqlite:///{}".format(tmp_path / "rbac.db")
    factory, engine = make_session_factory(url)
    path = tmp_path / "secrets.txt"
    provision(factory, path)
    # Do not keep database connections around outside the test API.
    engine.dispose()
    passwords = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if " [" in line and "]: " in line:
            name = line.split(" [", 1)[0]
            passwords[name] = line.split("]: ", 1)[1]
    return create_app(database_url=url, api_key="legacy-test-key"), factory, passwords


def login(c: TestClient, passwords: dict, username: str) -> str:
    response = c.post("/v1/auth/login", json={
        "username": username, "password": passwords[username],
    })
    assert response.status_code == 200, response.text
    return response.json()["access_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": "Bearer "+token}


def create_ticket(c: TestClient, index: int):
    r = c.post("/v1/handoffs",
        headers={"X-POC-Key": "legacy-test-key",
                 "Idempotency-Key": "test-auto-{}".format(index)},
        json={
            "external_conversation_id": "test-{}".format(index),
            "requester_label": "Teste {}".format(index),
            "subject": "Distribuição justa",
        })
    assert r.status_code == 201, r.text
    return r.json()["id"]


def test_passwords_and_server_rbac(tmp_path) -> None:
    app, _, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        assert c.post("/v1/auth/login", json={
            "username": "ana.demo", "password": "incorrect"
        }).status_code == 401
        ana = login(c, passwords, "ana.demo")
        supervisor = login(c, passwords, "supervisor.demo")
        auditor = login(c, passwords, "auditor.demo")
        bruno = login(c, passwords, "bruno.demo")
        assert c.get("/v1/auth/me", headers=auth(ana)).json()["operator_id"] == "op-ana"
        assert c.get("/v1/dashboard", headers=auth(ana)).status_code == 403
        assert c.get("/v1/operators/op-bruno/work", headers=auth(ana)).status_code == 403
        assert c.get("/v1/operators/op-ana/work", headers=auth(ana)).status_code == 200
        assert c.get("/v1/operators/op-ana/work", headers=auth(bruno)).status_code == 403
        assert c.get("/v1/dashboard", headers=auth(supervisor)).status_code == 200
        assert c.get("/v1/dashboard", headers=auth(auditor)).status_code == 200
        assert c.post("/v1/dispatch/offer", headers=auth(ana), json={}).status_code == 403
        assert c.post("/v1/handoffs", headers=auth(auditor), json={}).status_code == 403
        assert c.post("/v1/handoffs/x/messages", headers=auth(supervisor),
                      json={"sender": "OPERATOR", "content": "X",
                            "external_message_id": "123"}).status_code == 403
        assert c.get("/v1/outbox", headers=auth(auditor)).status_code == 403
        assert c.post("/v1/auth/logout", headers=auth(ana)).status_code == 200
        assert c.get("/v1/auth/me", headers=auth(ana)).status_code == 401


def test_round_robin_requires_online_operator_and_persists_turn(tmp_path) -> None:
    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        ana = login(c, passwords, "ana.demo")
        bruno = login(c, passwords, "bruno.demo")
        assert c.post("/v1/auth/heartbeat", headers=auth(ana)).status_code == 200
        assert c.post("/v1/auth/heartbeat", headers=auth(bruno)).status_code == 200
        sequence=[]
        for i in range(3):
            hid = create_ticket(c, i)
            assert run_dispatch_cycle(factory)["offered"] == 1
            with factory() as db:
                current = db.get(HandoffSession, hid)
                assert current.status == "OFFERED"
                sequence.append(current.operator_id)
            choice = ana if sequence[-1] == "op-ana" else bruno
            accepted = c.post("/v1/handoffs/{}/accept".format(hid),
                headers=auth(choice), json={"operator_id": sequence[-1]})
            assert accepted.status_code == 200
            closed = c.post(
                "/v1/operators/{}/handoffs/{}/close".format(sequence[-1], hid),
                headers=auth(choice),
            )
            assert closed.status_code == 200
        assert sequence == ["op-ana", "op-bruno", "op-ana"]
        order = c.get("/v1/queues/n1/rotation", headers=auth(
            login(c, passwords, "supervisor.demo")
        )).json()
        assert [x["operator_id"] for x in order["operators"]] == ["op-bruno", "op-ana"]


def test_operator_logout_removes_eligibility_and_requeues_offer(tmp_path) -> None:
    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        ana = login(c, passwords, "ana.demo")
        hid = create_ticket(c, 88)
        assert run_dispatch_cycle(factory)["offered"] == 1
        with factory() as db:
            assert db.get(HandoffSession, hid).operator_id == "op-ana"
        assert c.post("/v1/auth/logout", headers=auth(ana)).status_code == 200
        outcome=run_dispatch_cycle(factory)
        assert outcome["expired"] == 1
        with factory() as db:
            assert db.get(HandoffSession, hid).status == "QUEUED"
        bruno = login(c, passwords, "bruno.demo")
        assert c.post("/v1/auth/heartbeat", headers=auth(bruno)).status_code == 200
        assert run_dispatch_cycle(factory)["offered"] == 1
        with factory() as db:
            assert db.get(HandoffSession, hid).operator_id == "op-bruno"


def test_one_available_operator_can_receive_again_after_close(tmp_path) -> None:
    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        ana = login(c, passwords, "ana.demo")
        for i in range(2):
            hid = create_ticket(c, 200+i)
            assert run_dispatch_cycle(factory)["offered"] == 1
            with factory() as db:
                assert db.get(HandoffSession, hid).operator_id == "op-ana"
            assert c.post("/v1/handoffs/{}/accept".format(hid),
                headers=auth(ana), json={"operator_id": "op-ana"}).status_code == 200
            assert c.post("/v1/operators/op-ana/handoffs/{}/close".format(hid),
                headers=auth(ana)).status_code == 200
