"""Health and restricted-access tests for the local-only POC."""
from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app


def test_liveness(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path}/live.db", api_key="")
    with TestClient(app) as client:
        response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "alive"


def test_readiness_requires_explicit_poc_key(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path}/ready.db", api_key="")
    with TestClient(app) as client:
        response = client.get("/health/ready")
    assert response.status_code == 503
    assert response.json()["status"] == "not_ready"


def test_api_fails_closed_without_poc_key(tmp_path) -> None:
    app = create_app(database_url=f"sqlite:///{tmp_path}/denied.db", api_key="")
    with TestClient(app) as client:
        response = client.get("/v1/queues")
    assert response.status_code == 401
