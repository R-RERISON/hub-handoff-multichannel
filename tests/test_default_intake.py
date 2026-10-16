"""POC intake policy: default N1, explicit queue routing and safe legacy seed."""
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.auto_dispatch import run_dispatch_cycle
from handoff_hub.demo_routing import DEMO_ROUTING_REVISION
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    DemoSeedRevision,
    HandoffOffer,
    HandoffSession,
    QueueMembership,
    make_session_factory,
    utc_now,
)
from handoff_hub.seed_demo_auth import provision

LEGACY_KEY = {"X-POC-Key": "test-key"}


def environment(tmp_path: Path):
    url = f"sqlite:///{tmp_path / 'intake.db'}"
    factory, engine = make_session_factory(url)
    credentials = tmp_path / "credentials.txt"
    provision(factory, credentials)
    engine.dispose()
    return create_app(database_url=url, api_key="test-key"), factory, credentials


def handoff(client: TestClient, number: int, queue: str | None = None):
    body = {
        "external_conversation_id": f"chat-{number}",
        "requester_label": "Cliente de teste",
        "subject": "Intenção não classificada",
    }
    if queue is not None:
        body["queue_id"] = queue
    return client.post(
        "/v1/handoffs",
        headers={**LEGACY_KEY, "Idempotency-Key": f"intake-{number:06d}"},
        json=body,
    )


def test_new_demo_defaults_have_exclusive_n1_and_n2_membership(tmp_path) -> None:
    app, factory, _ = environment(tmp_path)
    with factory() as db:
        membership = set(db.execute(select(
            QueueMembership.queue_id, QueueMembership.operator_id
        )).all())
        assert membership == {("n1", "op-ana"), ("n2", "op-bruno")}
        assert db.get(DemoSeedRevision, DEMO_ROUTING_REVISION) is not None

    with TestClient(app) as client:
        default = handoff(client, 1)
        assert default.status_code == 201
        assert default.json()["queue_id"] == "n1"
        explicit = handoff(client, 2, queue="n2")
        assert explicit.status_code == 201
        assert explicit.json()["queue_id"] == "n2"
        invalid = handoff(client, 3, queue="nonexistent")
        assert invalid.status_code == 422
        repeated = handoff(client, 1)
        assert repeated.status_code == 201
        assert repeated.json()["id"] == default.json()["id"]


def test_bruno_online_cannot_take_generic_n1_but_can_take_explicit_n2(tmp_path) -> None:
    app, factory, creds = environment(tmp_path)
    contents = creds.read_text(encoding="utf-8")
    password = next(
        line.split("]: ", 1)[1] for line in contents.splitlines()
        if line.startswith("bruno.demo [")
    )
    with TestClient(app) as client:
        login = client.post("/v1/auth/login", json={
            "username": "bruno.demo", "password": password
        })
        assert login.status_code == 200
        n1 = handoff(client, 11)
        assert n1.status_code == 201
        assert run_dispatch_cycle(factory)["offered"] == 0
        with factory() as db:
            assert db.get(HandoffSession, n1.json()["id"]).status == "QUEUED"

        n2 = handoff(client, 12, queue="n2")
        assert n2.status_code == 201
        assert run_dispatch_cycle(factory)["offered"] == 1
        with factory() as db:
            n1_session = db.get(HandoffSession, n1.json()["id"])
            n2_session = db.get(HandoffSession, n2.json()["id"])
            assert n1_session.status == "QUEUED"
            assert n2_session.queue_id == "n2"
            assert n2_session.operator_id == "op-bruno"
            assert n2_session.status == "OFFERED"


def test_existing_demo_migrates_offered_and_preserves_active_and_custom_changes(tmp_path) -> None:
    app, factory, creds = environment(tmp_path)
    with factory.begin() as db:
        # Reconstruct the older POC baseline in a populated database.
        db.delete(db.get(DemoSeedRevision, DEMO_ROUTING_REVISION))
        db.add(QueueMembership(queue_id="n1", operator_id="op-bruno"))
        active = HandoffSession(
            operation_id="demo", integration_id="demo-bot", queue_id="n1",
            requester_label="Ativo", subject="Preservar atendimento existente",
            external_conversation_id="legacy-active", idempotency_key="legacy-active",
            status="ACTIVE", operator_id="op-bruno",
        )
        offered = HandoffSession(
            operation_id="demo", integration_id="demo-bot", queue_id="n1",
            requester_label="Ofertado", subject="Liberar oferta",
            external_conversation_id="legacy-offer", idempotency_key="legacy-offer",
            status="OFFERED", operator_id="op-bruno",
        )
        db.add_all((active, offered))
        db.flush()
        active_id, offered_id = active.id, offered.id
        db.add(HandoffOffer(
            session_id=offered.id, operator_id="op-bruno", status="PENDING",
            expires_at=utc_now(),
        ))

    provision(factory, creds)  # Apply migration once, do not replace credentials.
    with factory() as db:
        assert db.get(QueueMembership, ("n1", "op-bruno")) is None
        assert db.get(HandoffSession, active_id).status == "ACTIVE"
        assert db.get(HandoffSession, active_id).operator_id == "op-bruno"
        migrated = db.get(HandoffSession, offered_id)
        assert migrated.status == "QUEUED"
        assert migrated.queue_id == "n1"
        assert migrated.operator_id is None
        offer = db.scalar(select(HandoffOffer).where(HandoffOffer.session_id == offered_id))
        assert offer.status == "EXPIRED"

    # Subsequent administrator changes to routing must survive restart.
    with factory.begin() as db:
        db.add(QueueMembership(queue_id="n1", operator_id="op-bruno"))
    provision(factory, creds)
    with factory() as db:
        assert db.get(QueueMembership, ("n1", "op-bruno")) is not None
