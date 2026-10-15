"""SPEC-003 local SQLite gates: offers, operator decisions, transfers and capacity."""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from sqlite3 import connect as connect_sqlite

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app

AUTH = {"X-POC-Key": "local-test"}


def create_handoff(client: TestClient, number: int, queue_id: str = "n1") -> str:
    res = client.post(
        "/v1/handoffs",
        headers={**AUTH, "Idempotency-Key": f"workflow-{number:05d}"},
        json={
            "external_conversation_id": f"conversation-{number}",
            "requester_label": f"Pessoa simulada {number}",
            "subject": "Suporte simulado",
            "queue_id": queue_id,
        },
    )
    assert res.status_code == 201, res.text
    return res.json()["id"]


def app_for(tmp_path):
    return create_app(database_url=f"sqlite:///{tmp_path}/spec003.db", api_key="local-test")


def test_offer_accept_transfer_reoffer_and_close(tmp_path) -> None:
    with TestClient(app_for(tmp_path)) as c:
        assert c.post("/v1/demo/bootstrap", headers=AUTH).status_code == 200
        handoff_id = create_handoff(c, 1)
        offer = c.post("/v1/dispatch/offer", headers=AUTH, json={})
        assert offer.status_code == 200
        assert offer.json()["result"] == "offered"
        operator_id = offer.json()["offer"]["operator_id"]
        assert offer.json()["offer"]["session_id"] == handoff_id

        snapshot = c.get("/v1/dashboard", headers=AUTH).json()
        assert snapshot["handoffs"][0]["status"] == "OFFERED"
        chosen = next(op for op in snapshot["operators"] if op["id"] == operator_id)
        assert chosen["offered"] == 1
        inbox = c.get(f"/v1/operators/{operator_id}/work", headers=AUTH).json()
        assert len(inbox["offers"]) == 1

        bad_actor = "op-bruno" if operator_id == "op-ana" else "op-ana"
        assert c.post(f"/v1/handoffs/{handoff_id}/accept",
                      headers=AUTH, json={"operator_id": bad_actor}).status_code == 409
        accepted = c.post(f"/v1/handoffs/{handoff_id}/accept",
                          headers=AUTH, json={"operator_id": operator_id})
        assert accepted.status_code == 200, accepted.text
        assert accepted.json()["status"] == "ACTIVE"
        assert c.post(f"/v1/handoffs/{handoff_id}/accept",
                      headers=AUTH, json={"operator_id": operator_id}).status_code == 409
        assert c.get(f"/v1/operators/{operator_id}/work", headers=AUTH).json()["active"]

        wrong_message = c.post(
            f"/v1/handoffs/{handoff_id}/messages", headers=AUTH,
            json={"sender": "OPERATOR", "operator_id": bad_actor,
                  "content": "texto", "external_message_id": "unauthorized-msg"},
        )
        assert wrong_message.status_code == 403
        good_message = c.post(
            f"/v1/handoffs/{handoff_id}/messages", headers=AUTH,
            json={"sender": "OPERATOR", "operator_id": operator_id,
                  "content": "Atendendo", "external_message_id": "operator-msg"},
        )
        assert good_message.status_code == 201

        transfer = c.post(
            f"/v1/handoffs/{handoff_id}/transfer",
            headers=AUTH,
            json={"operator_id": operator_id, "queue_id": "n2",
                  "reason": "Especialidade do suporte N2"},
        )
        assert transfer.status_code == 200, transfer.text
        assert transfer.json()["status"] == "QUEUED"
        assert transfer.json()["operator_id"] is None
        assert transfer.json()["queue_id"] == "n2"
        assert c.post(f"/v1/handoffs/{handoff_id}/transfer", headers=AUTH,
                      json={"operator_id": operator_id, "queue_id": "n2",
                            "reason": "Novamente"}).status_code == 409

        timeline = c.get(f"/v1/handoffs/{handoff_id}/timeline", headers=AUTH).json()
        assert timeline["transfers"][0]["reason"] == "Especialidade do suporte N2"
        assert "TRANSFERRED" in {e["type"] for e in timeline["events"]}

        n2 = c.post("/v1/dispatch/offer", headers=AUTH, json={"queue_id": "n2"})
        assert n2.json()["result"] == "offered"
        assert n2.json()["offer"]["operator_id"] == "op-bruno"
        assert c.post(f"/v1/handoffs/{handoff_id}/accept", headers=AUTH,
                      json={"operator_id": "op-bruno"}).status_code == 200
        assert c.post(f"/v1/handoffs/{handoff_id}/close", headers=AUTH).json()["status"] == "CLOSED"
        assert c.get("/v1/dashboard", headers=AUTH).json()["outbox"]["pending"] == 1


def test_decline_returns_session_to_queue_and_skips_same_operator(tmp_path) -> None:
    with TestClient(app_for(tmp_path)) as c:
        c.post("/v1/demo/bootstrap", headers=AUTH)
        handoff_id = create_handoff(c, 2)
        first = c.post("/v1/dispatch/offer", headers=AUTH, json={}).json()["offer"]
        result = c.post(f"/v1/handoffs/{handoff_id}/decline", headers=AUTH,
                        json={"operator_id": first["operator_id"]})
        assert result.status_code == 200
        assert result.json()["status"] == "QUEUED"
        assert result.json()["operator_id"] is None
        assert c.post(f"/v1/handoffs/{handoff_id}/decline", headers=AUTH,
                      json={"operator_id": first["operator_id"]}).status_code == 409
        second = c.post("/v1/dispatch/offer", headers=AUTH, json={}).json()["offer"]
        assert second["operator_id"] != first["operator_id"]


def test_expiry_and_late_accept(tmp_path) -> None:
    database = tmp_path / "spec003.db"
    with TestClient(app_for(tmp_path)) as c:
        c.post("/v1/demo/bootstrap", headers=AUTH)
        handoff_id = create_handoff(c, 3)
        selected = c.post("/v1/dispatch/offer", headers=AUTH, json={}).json()["offer"]
        past = (datetime.now(UTC) - timedelta(minutes=10)).replace(
            tzinfo=None
        ).isoformat(sep=" ")
        with connect_sqlite(database) as db:
            db.execute("UPDATE handoff_offers SET expires_at = ? WHERE id = ?",
                       (past, selected["offer_id"]))
        expired = c.post("/v1/offers/expire", headers=AUTH)
        assert expired.status_code == 200
        assert expired.json()["expired"] == 1
        assert c.post(f"/v1/handoffs/{handoff_id}/accept", headers=AUTH,
                      json={"operator_id": selected["operator_id"]}).status_code == 409
        snapshot = c.get("/v1/dashboard", headers=AUTH).json()
        assert snapshot["handoffs"][0]["status"] == "QUEUED"
        assert sum(op["offered"] for op in snapshot["operators"]) == 0


def test_parallel_offer_reserves_only_one_seat(tmp_path) -> None:
    app = app_for(tmp_path)
    with TestClient(app) as c:
        c.post("/v1/demo/bootstrap", headers=AUTH)
        c.patch("/v1/operators/op-bruno/presence", headers=AUTH,
                json={"presence": "OFFLINE"})
        create_handoff(c, 4)
        create_handoff(c, 5)

        def attempt(_):
            with TestClient(app) as isolated:
                return isolated.post("/v1/dispatch/offer", headers=AUTH, json={}).json()

        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, range(2)))
        assert sorted(x["result"] for x in results) == ["no_operator_available", "offered"]
        snapshot = c.get("/v1/dashboard", headers=AUTH).json()
        assert sum(op["offered"] + op["active"] for op in snapshot["operators"]) == 1


def test_transfer_rejects_wrong_operator_and_invalid_queue(tmp_path) -> None:
    with TestClient(app_for(tmp_path)) as c:
        c.post("/v1/demo/bootstrap", headers=AUTH)
        handoff_id = create_handoff(c, 6)
        offer = c.post("/v1/dispatch/offer", headers=AUTH, json={}).json()["offer"]
        operator_id = offer["operator_id"]
        c.post(f"/v1/handoffs/{handoff_id}/accept", headers=AUTH,
               json={"operator_id": operator_id})
        other = "op-bruno" if operator_id == "op-ana" else "op-ana"
        wrong = c.post(f"/v1/handoffs/{handoff_id}/transfer", headers=AUTH,
                       json={"operator_id": other, "queue_id": "n2", "reason": "Nao autorizado"})
        assert wrong.status_code == 409
        invalid = c.post(f"/v1/handoffs/{handoff_id}/transfer", headers=AUTH,
                         json={"operator_id": operator_id, "queue_id": "invalid",
                               "reason": "Fila inexistente"})
        assert invalid.status_code == 422
        assert c.get("/v1/dashboard", headers=AUTH).json()["handoffs"][0]["status"] == "ACTIVE"


def test_original_demo_dispatch_respects_pending_offers(tmp_path) -> None:
    with TestClient(app_for(tmp_path)) as c:
        c.post("/v1/demo/bootstrap", headers=AUTH)
        c.patch("/v1/operators/op-bruno/presence", headers=AUTH,
                json={"presence": "OFFLINE"})
        create_handoff(c, 7)
        create_handoff(c, 8)
        assert c.post("/v1/dispatch/offer", headers=AUTH, json={}).json()["result"] == "offered"
        response = c.post("/v1/dispatch/next", headers=AUTH, json={}).json()
        assert response["result"] == "no_operator_available"
