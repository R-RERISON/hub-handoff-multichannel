"""Foundation probes must not imply a real operational service."""

from fastapi.testclient import TestClient

from handoff_hub.main import app

client = TestClient(app)


def test_liveness() -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}


def test_readiness_is_not_false_positive() -> None:
    response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_operational_endpoint_is_not_exposed() -> None:
    response = client.post("/v1/handoffs", json={})
    assert response.status_code == 404
