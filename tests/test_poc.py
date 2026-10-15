"""API and SQLite concurrency gates: local only, no GitHub Actions."""
from concurrent.futures import ThreadPoolExecutor

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app


def test_poc_workflow(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path}/flow.db", api_key="test-local")
    with TestClient(app) as c:
        def req(method, path, **kw):
            headers = {"X-POC-Key": "test-local", **kw.pop("headers", {})}
            return c.request(method, path, headers=headers, **kw)
        assert req("POST", "/v1/demo/bootstrap").status_code == 200
        assert req("POST", "/v1/demo/bootstrap").status_code == 200
        body = {"external_conversation_id": "conversation-01",
                "requester_label": "Usuário simulado", "subject": "Acesso"}
        h = req("POST", "/v1/handoffs", json=body,
                headers={"Idempotency-Key": "test-key-0001"})
        assert h.status_code == 201, h.text
        h_id = h.json()["id"]
        assert req("POST", "/v1/handoffs", json=body,
                   headers={"Idempotency-Key": "test-key-0001"}).json()["id"] == h_id
        assert req("POST", "/v1/handoffs", json=dict(body, subject="Incompatível"),
                   headers={"Idempotency-Key": "test-key-0001"}).status_code == 409
        assert req("POST", "/v1/handoffs", json=dict(body, queue_id="invalid"),
                   headers={"Idempotency-Key": "test-key-invalid"}).status_code == 422
        response = req("POST", "/v1/dispatch/next", json={})
        assert response.json()["result"] == "assigned"
        assert response.json()["session"]["id"] == h_id
        assert req("POST", f"/v1/handoffs/{h_id}/messages",
                   json={"sender": "USER", "content": "Olá",
                         "external_message_id": "test-msg-1"}).status_code == 201
        message = {"sender": "OPERATOR", "content": "Vou ajudar",
                   "external_message_id": "test-msg-2"}
        assert req("POST", f"/v1/handoffs/{h_id}/messages", json=message).status_code == 201
        assert req("POST", f"/v1/handoffs/{h_id}/messages",
                   json=message).json()["status"] == "duplicate"
        assert len(req("GET", f"/v1/handoffs/{h_id}/messages").json()) == 2
        events = req("GET", "/v1/outbox").json()
        assert len(events) == 1 and events[0]["status"] == "PENDING_ADAPTER"
        assert req("POST", f"/v1/handoffs/{h_id}/close").json()["status"] == "CLOSED"
        assert req("POST", f"/v1/handoffs/{h_id}/close").json()["status"] == "CLOSED"
        assert req("POST", f"/v1/handoffs/{h_id}/messages", json=message).status_code == 409
        assert c.get("/v1/operators").status_code == 401


def test_parallel_dispatch_does_not_overallocate(tmp_path):
    app = create_app(database_url=f"sqlite:///{tmp_path}/concurrency.db", api_key="test-local")
    headers = {"X-POC-Key": "test-local"}
    with TestClient(app) as client:
        assert client.post("/v1/demo/bootstrap", headers=headers).status_code == 200
        assert client.patch("/v1/operators/op-bruno/presence",
                            headers=headers, json={"presence": "OFFLINE"}).status_code == 200
        for i in range(2):
            assert client.post("/v1/handoffs",
                               headers={**headers, "Idempotency-Key": f"test-parallel-{i}"},
                               json={"external_conversation_id": f"conv-{i}",
                                     "requester_label": f"Usuário {i}",
                                     "subject": "Acesso"}).status_code == 201

        def dispatch(_):
            with TestClient(app) as other_client:
                return other_client.post("/v1/dispatch/next", headers=headers, json={}).json()

        with ThreadPoolExecutor(max_workers=2) as workers:
            results = list(workers.map(dispatch, range(2)))
        assert sorted(x["result"] for x in results) == ["assigned", "no_operator_available"]
        operators = client.get("/v1/operators", headers=headers).json()
        assert sum(x["active"] for x in operators) == 1
