"""Dashboard aggregation contract and security regression tests for SQLite POC."""

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app


def test_dashboard_snapshot_lifecycle(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path}/dashboard.db", api_key="local-test")
    headers = {"X-POC-Key": "local-test"}

    with TestClient(app) as client:
        assert client.get("/v1/dashboard").status_code == 401
        assert client.get("/v1/dashboard", headers=headers).status_code == 200

        assert client.post("/v1/demo/bootstrap", headers=headers).status_code == 200
        initial = client.get("/v1/dashboard", headers=headers).json()
        assert initial["handoffs"] == []
        assert initial["queues"][0]["waiting"] == 0
        assert len(initial["operators"]) == 2
        assert initial["outbox"] == {"total": 0, "pending": 0}

        created = client.post(
            "/v1/handoffs",
            headers={**headers, "Idempotency-Key": "dashboard-test-001"},
            json={
                "external_conversation_id": "synthetic-connection",
                "requester_label": "Pessoa simulada",
                "subject": "Acesso de teste",
            },
        )
        assert created.status_code == 201
        handoff_id = created.json()["id"]

        waiting = client.get("/v1/dashboard", headers=headers).json()
        assert waiting["queues"][0]["waiting"] == 1
        assert waiting["handoffs"][0]["id"] == handoff_id

        assigned = client.post("/v1/dispatch/next", headers=headers, json={})
        assert assigned.status_code == 200
        assert assigned.json()["result"] == "assigned"
        active = client.get("/v1/dashboard", headers=headers).json()
        assert active["queues"][0]["waiting"] == 0
        assert sum(op["active"] for op in active["operators"]) == 1

        response = client.post(
            f"/v1/handoffs/{handoff_id}/messages",
            headers=headers,
            json={
                "sender": "OPERATOR",
                "content": "Mensagem de demonstração: não enviar ao Teams",
                "external_message_id": "operator-msg-001",
            },
        )
        assert response.status_code == 201
        pending = client.get("/v1/dashboard", headers=headers).json()
        assert pending["outbox"] == {"total": 1, "pending": 1}
        assert "Mensagem de demonstração" not in str(pending)

        closed = client.post(f"/v1/handoffs/{handoff_id}/close", headers=headers)
        assert closed.status_code == 200
        finished = client.get("/v1/dashboard", headers=headers).json()
        assert finished["handoffs"][0]["status"] == "CLOSED"
        assert sum(op["active"] for op in finished["operators"]) == 0
        # No channel adapter exists. Closing a chat does not mark its messages delivered.
        assert finished["outbox"]["pending"] == 1
