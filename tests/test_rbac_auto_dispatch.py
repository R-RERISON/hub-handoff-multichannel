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


def test_login_lockout_is_persistent_and_revokes_access(tmp_path) -> None:
    app, _, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        for _ in range(5):
            assert c.post("/v1/auth/login", json={
                "username": "ana.demo", "password": "incorrect-password"
            }).status_code == 401
        assert c.post("/v1/auth/login", json={
            "username": "ana.demo", "password": passwords["ana.demo"]
        }).status_code == 429
        # Accounts not involved in the failures remain accessible.
        assert login(c, passwords, "bruno.demo")


def test_supervisor_manages_membership_and_capacity_safely(tmp_path) -> None:
    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        supervisor = auth(login(c, passwords, "supervisor.demo"))
        ana = auth(login(c, passwords, "ana.demo"))
        unauthorized = c.patch("/v1/operators/op-bruno/capacity",
                               headers=ana, json={"capacity": 2})
        assert unauthorized.status_code == 403
        update = c.patch("/v1/operators/op-ana/capacity",
                         headers=supervisor, json={"capacity": 2})
        assert update.status_code == 200
        assert update.json()["capacity"] == 2
        assert c.patch("/v1/operators/op-ana/capacity",
                       headers=supervisor, json={"capacity": 0}).status_code == 422
        # N2 has Bruno only. A supervisor may enable Ana.
        added = c.patch("/v1/queues/n2/members/op-ana",
                        headers=supervisor, json={"enabled": True})
        assert added.status_code == 200
        order = c.get("/v1/queues/n2/rotation", headers=supervisor).json()
        assert {op["operator_id"] for op in order["operators"]} == {
            "op-ana", "op-bruno"
        }
        # Existing queue members are never removed while reserved.
        hid = create_ticket(c, 122)
        assert run_dispatch_cycle(factory)["offered"] == 1
        reject = c.patch("/v1/queues/n1/members/op-ana", headers=supervisor,
                         json={"enabled": False})
        assert reject.status_code == 409
        assert c.patch("/v1/queues/n2/members/op-ana", headers=supervisor,
                       json={"enabled": False}).status_code == 200


def test_automatic_n1_to_n2_transfer_requires_online_bruno(tmp_path) -> None:
    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        ana = auth(login(c, passwords, "ana.demo"))
        handoff = create_ticket(c, 123)
        assert run_dispatch_cycle(factory)["offered"] == 1
        accepted = c.post("/v1/handoffs/{}/accept".format(handoff),
                          headers=ana, json={"operator_id": "op-ana"})
        assert accepted.status_code == 200
        transfer = c.post("/v1/handoffs/{}/transfer".format(handoff),
                          headers=ana, json={
                              "operator_id": "op-ana", "queue_id": "n2",
                              "reason": "Exige suporte especializado N2"
                          })
        assert transfer.status_code == 200
        # Bruno is not logged in; queue cannot auto-offer to him.
        assert run_dispatch_cycle(factory)["offered"] == 0
        with factory() as db:
            assert db.get(HandoffSession, handoff).status == "QUEUED"
        bruno = auth(login(c, passwords, "bruno.demo"))
        assert run_dispatch_cycle(factory)["offered"] == 1
        with factory() as db:
            h = db.get(HandoffSession, handoff)
            assert h.status == "OFFERED"
            assert h.queue_id == "n2"
            assert h.operator_id == "op-bruno"
        assert c.get("/v1/operators/op-bruno/work", headers=bruno).json()["offers"]


def test_fifo_and_capacity_under_parallel_cycle(tmp_path) -> None:
    """A second simultaneous writer must not double-offer a reserved seat."""
    from concurrent.futures import ThreadPoolExecutor

    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        login(c, passwords, "ana.demo")
        login(c, passwords, "bruno.demo")
        ids = [create_ticket(c, 300 + i) for i in range(3)]

        def dispatch(_):
            return run_dispatch_cycle(factory)

        with ThreadPoolExecutor(max_workers=2) as pool:
            list(pool.map(dispatch, range(2)))
        with factory() as db:
            rows = [db.get(HandoffSession, hid) for hid in ids]
            assert [h.status for h in rows] == ["OFFERED", "OFFERED", "QUEUED"]
            assert {h.operator_id for h in rows[:2]} == {"op-ana", "op-bruno"}
            assert rows[-1].operator_id is None


def test_reset_credentials_revokes_tokens(tmp_path) -> None:
    app, factory, passwords = setup_poc(tmp_path)
    path = tmp_path / "secrets.txt"
    with TestClient(app) as c:
        old_token = login(c, passwords, "ana.demo")
        assert c.get("/v1/auth/me", headers=auth(old_token)).status_code == 200
        provision(factory, path, reset=True)
        assert c.get("/v1/auth/me", headers=auth(old_token)).status_code == 401
        old_login = c.post("/v1/auth/login", json={
            "username": "ana.demo", "password": passwords["ana.demo"],
        })
        assert old_login.status_code == 401


def test_expired_offer_reenters_queue_without_duplicate_reservations(tmp_path) -> None:
    from datetime import UTC, datetime, timedelta

    from sqlalchemy import text

    app, factory, passwords = setup_poc(tmp_path)
    with TestClient(app) as c:
        login(c, passwords, "ana.demo")
        hid = create_ticket(c, 400)
        assert run_dispatch_cycle(factory)["offered"] == 1
        with factory.begin() as db:
            db.execute(
                text("UPDATE handoff_offers SET expires_at=:expiry WHERE session_id=:sid"),
                {"expiry": (datetime.now(UTC) - timedelta(minutes=5)).replace(
                    tzinfo=None
                ).isoformat(sep=" "), "sid": hid},
            )
        result = run_dispatch_cycle(factory)
        assert result["expired"] == 1
        assert result["offered"] == 0  # cooldown prevents immediate reoffer to Ana
        with factory() as db:
            h = db.get(HandoffSession, hid)
            assert h.status == "QUEUED"
            assert h.operator_id is None
