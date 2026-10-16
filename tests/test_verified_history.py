"""SPEC-006B-4.1: authenticated isolation for runtime-verified queue history.

All data is synthetic and every DB is created under tmp_path.
"""
import pytest
from alembic import command
from fastapi.testclient import TestClient
from sqlalchemy import insert, select, text, update

from handoff_hub.audit_schema import HISTORY_ACCESS_AUDIT
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import (
    AuthUser,
    HandoffSession,
    SessionEvent,
    SessionTransfer,
    make_session_factory,
)
from handoff_hub.provenance_schema import (
    MESSAGE_QUEUE_PROVENANCE,
    SESSION_EVENT_QUEUE_PROVENANCE,
    SESSION_QUEUE_SEGMENTS,
)
from handoff_hub.schema_admin import (
    AUDIT_REVISION,
    PROVENANCE_REVISION,
    _config,
    create_new,
    verify_database,
)
from handoff_hub.security_schema import SECURITY_DECISIONS
from handoff_hub.seed_demo_auth import provision

KEY = {"X-POC-Key": "local-test-only"}
BASE = "/v1/handoffs"


def environment(tmp_path, *, versioned=True):
    path = tmp_path / ("verified.db" if versioned else "original.db")
    if versioned:
        create_new(path, confirmed=True)
    url = f"sqlite:///{path.as_posix()}"
    factory, engine = make_session_factory(url)
    credentials = tmp_path / "credentials.txt"
    provision(factory, credentials)
    passwords = {
        line.split(" [", 1)[0]: line.split("]: ", 1)[1]
        for line in credentials.read_text(encoding="utf-8").splitlines()
        if " [" in line and "]: " in line
    }
    engine.dispose()
    return create_app(database_url=url, api_key="local-test-only"), factory, passwords


def bearer(client, passwords, name):
    response = client.post("/v1/auth/login", json={
        "username": name, "password": passwords[name],
    })
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def new_ticket(client, suffix):
    response = client.post(
        BASE, headers={**KEY, "Idempotency-Key": f"verified-{suffix}"},
        json={
            "operation_id": "demo",
            "integration_id": "demo-bot",
            "queue_id": "n1",
            "requester_label": "Pessoa sintética",
            "subject": "Teste segregado",
            "external_conversation_id": f"demo-{suffix}",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()["id"]


def user_message(client, hid, name):
    response = client.post(f"{BASE}/{hid}/messages", headers=KEY, json={
        "sender": "USER", "content": name, "external_message_id": f"ext-{name}",
    })
    assert response.status_code == 201, response.text
    return response.json()["id"]


def transfer(client, factory, hid):
    with factory.begin() as db:
        row = db.get(HandoffSession, hid)
        row.status = "ACTIVE"
        row.operator_id = "op-ana"
    response = client.post(f"{BASE}/{hid}/transfer", headers=KEY, json={
        "operator_id": "op-ana", "queue_id": "n2",
        "reason": "Nota interna secreta da transferência",
    })
    assert response.status_code == 200, response.text


def history(client, hid, queue, headers):
    return client.get(f"{BASE}/{hid}/verified-history", params={
        "queue_id": queue,
    }, headers=headers)


def test_scoped_n1_and_n2_receive_only_own_verified_history(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        admin = bearer(client, passwords, "admin.demo")
        ana = bearer(client, passwords, "ana.demo")
        hid = new_ticket(client, "two-queues")
        n1id = user_message(client, hid, "Mensagem somente N1")
        transfer(client, factory, hid)
        n2id = user_message(client, hid, "Mensagem somente N2")

        n1 = history(client, hid, "n1", auditor)
        assert n1.status_code == 200, n1.text
        assert n1.json()["scope"] == "RUNTIME_VERIFIED_QUEUE_ONLY"
        assert n1.json()["partial_history"] is True
        assert [m["id"] for m in n1.json()["messages"]] == [n1id]
        assert {e["type"] for e in n1.json()["events"]} == {"QUEUED", "TRANSFERRED"}
        assert "Nota interna secreta" not in n1.text
        assert "Mensagem somente N2" not in n1.text
        assert "n2" not in n1.text

        n2 = history(client, hid, "n2", supervisor)
        assert n2.status_code == 200, n2.text
        assert [m["id"] for m in n2.json()["messages"]] == [n2id]
        assert "Mensagem somente N1" not in n2.text
        assert "Nota interna secreta" not in n2.text

        assert history(client, hid, "n2", auditor).status_code == 404
        assert history(client, hid, "n1", admin).status_code == 403
        assert history(client, hid, "n1", ana).status_code == 403
        assert history(client, hid, "n1", {}).status_code == 401
        assert history(client, "not-a-handoff", "n1", auditor).status_code == 404
        # Full-history routes stay blocked for scoped users; operator flow unchanged.
        assert client.get(f"{BASE}/{hid}/messages", headers=supervisor).status_code == 403
        assert client.get(f"{BASE}/{hid}/timeline", headers=supervisor).status_code == 403
        assert client.get(f"{BASE}/{hid}/messages", headers=KEY).status_code == 200


def test_grant_revocation_is_effective_on_next_read(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        admin = bearer(client, passwords, "admin.demo")
        hid = new_ticket(client, "revocation")
        user_message(client, hid, "Conteúdo protegido")
        assert history(client, hid, "n1", auditor).status_code == 200
        with factory() as db:
            uid = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "auditor.demo",
            ))
        revoked = client.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n1",
            "role": "AUDITOR", "enabled": False,
        })
        assert revoked.status_code == 200, revoked.text
        assert history(client, hid, "n1", auditor).status_code == 404


def test_unverified_and_non_runtime_rows_never_appear(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "unverified")
        first = user_message(client, hid, "Aprovada")
        second = user_message(client, hid, "Sem confiança")
        third = user_message(client, hid, "Origem não runtime")
        with factory.begin() as db:
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == second)
                .values(confidence="UNDETERMINED")
            )
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == third)
                .values(assigned_by="MIGRATION")
            )
            queued = db.scalar(select(SessionEvent.id).where(
                SessionEvent.session_id == hid,
                SessionEvent.event_type == "QUEUED",
            ))
            db.execute(
                update(SESSION_EVENT_QUEUE_PROVENANCE)
                .where(SESSION_EVENT_QUEUE_PROVENANCE.c.event_id == queued)
                .values(confidence="UNDETERMINED")
            )
        result = history(client, hid, "n1", auditor)
        assert result.status_code == 200, result.text
        assert [m["id"] for m in result.json()["messages"]] == [first]
        assert result.json()["events"] == []


def test_invalid_cross_session_segment_reference_cannot_grant_access(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid1 = new_ticket(client, "first")
        m1 = user_message(client, hid1, "Compartimentada")
        hid2 = new_ticket(client, "second")
        m2 = user_message(client, hid2, "Segundo ticket")
        with factory.begin() as db:
            foreign_segment = db.scalar(select(SESSION_QUEUE_SEGMENTS.c.id).where(
                SESSION_QUEUE_SEGMENTS.c.session_id == hid2,
            ))
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == m1)
                .values(segment_id=foreign_segment)
            )
        result1 = history(client, hid1, "n1", auditor)
        result2 = history(client, hid2, "n1", auditor)
        assert result1.status_code == 200
        assert result1.json()["messages"] == []
        assert [m["id"] for m in result2.json()["messages"]] == [m2]


def test_original_unversioned_db_never_unlocks_history(tmp_path):
    app, factory, passwords = environment(tmp_path, versioned=False)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        hid = new_ticket(client, "old-db")
        user_message(client, hid, "Histórico POC")
        transfer(client, factory, hid)
        assert history(client, hid, "n1", auditor).status_code == 404
        assert client.get(f"{BASE}/{hid}/messages", headers=supervisor).status_code == 403
        assert client.get(f"{BASE}/{hid}/timeline", headers=supervisor).status_code == 403
    with factory() as db:
        tables = set(db.scalars(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).all())
        assert len(tables) == 17
        assert "session_queue_segments" not in tables
        assert "alembic_version" not in tables


def test_versioned_legacy_ticket_without_segment_is_not_reconstructed(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with factory.begin() as db:
        # This row predates the runtime recorder. The current queue and even
        # an explicit transfer do not prove the ownership of old chat content.
        row = HandoffSession(
            operation_id="demo", integration_id="demo-bot", queue_id="n2",
            external_conversation_id="old-conversation",
            requester_label="Pessoa sintética", subject="Legado",
            idempotency_key="old-unverified", status="QUEUED",
        )
        db.add(row)
        db.flush()
        db.add(SessionTransfer(
            session_id=row.id, from_queue_id="n1", to_queue_id="n2",
            from_operator_id="op-ana", reason="Histórico não comprovado",
        ))
        hid = row.id
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        assert history(client, hid, "n1", auditor).status_code == 404
        assert history(client, hid, "n2", supervisor).status_code == 404
        assert client.get(f"{BASE}/{hid}/messages", headers=supervisor).status_code == 403


def verified_listing(client, queue, headers, **options):
    return client.get(
        "/v1/history/verified-sessions",
        params={"queue_id": queue, **options},
        headers=headers,
    )


def test_verified_discovery_is_authorized_and_does_not_expose_other_queue(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        admin = bearer(client, passwords, "admin.demo")
        ana = bearer(client, passwords, "ana.demo")
        transferred = new_ticket(client, "discover-transferred")
        user_message(client, transferred, "Conteúdo exclusivo N1")
        transfer(client, factory, transferred)
        user_message(client, transferred, "Conteúdo exclusivo N2")
        n1_only = new_ticket(client, "discover-n1-only")
        user_message(client, n1_only, "Outra N1")

        n1 = verified_listing(client, "n1", auditor)
        assert n1.status_code == 200, n1.text
        assert n1.json()["schema_ready"] is True
        assert n1.json()["partial_history"] is True
        assert {row["session_id"] for row in n1.json()["tickets"]} == {
            transferred, n1_only,
        }
        assert all(set(row) == {"session_id", "segment_started_at"}
                   for row in n1.json()["tickets"])
        assert "Conteúdo exclusivo N2" not in n1.text
        assert "requester_label" not in n1.text
        assert "subject" not in n1.text
        assert "current_queue" not in n1.text
        assert "reason" not in n1.text

        n2 = verified_listing(client, "n2", supervisor)
        assert n2.status_code == 200, n2.text
        assert [row["session_id"] for row in n2.json()["tickets"]] == [transferred]
        assert verified_listing(client, "n2", auditor).status_code == 404
        assert verified_listing(client, "n1", admin).status_code == 403
        assert verified_listing(client, "n1", ana).status_code == 403
        assert verified_listing(client, "n1", {}).status_code == 401
        assert verified_listing(client, "missing", auditor).status_code == 404


def test_verified_discovery_pages_and_grant_revocation(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        admin = bearer(client, passwords, "admin.demo")
        auditor = bearer(client, passwords, "auditor.demo")
        ids = []
        for suffix in ("page-a", "page-b", "page-c"):
            hid = new_ticket(client, suffix)
            user_message(client, hid, suffix)
            ids.append(hid)

        found = []
        for page in (1, 2, 3):
            result = verified_listing(
                client, "n1", auditor, page=page, page_size=1,
            )
            assert result.status_code == 200, result.text
            assert result.json()["page"] == page
            found.extend(row["session_id"] for row in result.json()["tickets"])
            assert result.json()["next_page"] == (page + 1 if page < 3 else None)
        assert set(found) == set(ids)
        assert verified_listing(client, "n1", auditor, page_size=0).status_code == 422
        assert verified_listing(client, "n1", auditor, page_size=51).status_code == 422

        with factory() as db:
            uid = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "auditor.demo",
            ))
        revoke = client.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n1",
            "role": "AUDITOR", "enabled": False,
        })
        assert revoke.status_code == 200
        assert verified_listing(client, "n1", auditor).status_code == 404


def test_discovery_excludes_unproven_legacy_and_untrusted_records(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        good = new_ticket(client, "discovery-good")
        user_message(client, good, "Bom")
        untrusted = new_ticket(client, "discovery-untrusted")
        message_id = user_message(client, untrusted, "Confiança inválida")
        with factory.begin() as db:
            event_id = db.scalar(select(SessionEvent.id).where(
                SessionEvent.session_id == untrusted,
                SessionEvent.event_type == "QUEUED",
            ))
            db.execute(
                update(MESSAGE_QUEUE_PROVENANCE)
                .where(MESSAGE_QUEUE_PROVENANCE.c.message_id == message_id)
                .values(confidence="UNDETERMINED")
            )
            db.execute(
                update(SESSION_EVENT_QUEUE_PROVENANCE)
                .where(SESSION_EVENT_QUEUE_PROVENANCE.c.event_id == event_id)
                .values(confidence="UNDETERMINED")
            )
            legacy = HandoffSession(
                operation_id="demo", integration_id="demo-bot", queue_id="n1",
                external_conversation_id="legacy-discovery",
                requester_label="Legado", subject="Sem prova",
                idempotency_key="legacy-discovery-only", status="QUEUED",
            )
            db.add(legacy)
            db.flush()
            legacy_id = legacy.id
        result = verified_listing(client, "n1", auditor)
        assert result.status_code == 200, result.text
        assert [r["session_id"] for r in result.json()["tickets"]] == [good]
        assert untrusted not in result.text
        assert legacy_id not in result.text


def test_unversioned_verified_discovery_reports_explicit_unavailability(tmp_path):
    app, factory, passwords = environment(tmp_path, versioned=False)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "unversioned-list")
        user_message(client, hid, "POC sem migração")
        result = verified_listing(client, "n1", auditor)
        assert result.status_code == 200, result.text
        assert result.json()["schema_ready"] is False
        assert result.json()["tickets"] == []
        assert result.json()["partial_history"] is True
        assert hid not in result.text
    with factory() as db:
        tables = set(db.scalars(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).all())
        assert len(tables) == 17


def test_verified_detail_has_independent_bounded_message_and_event_pages(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        supervisor = bearer(client, passwords, "supervisor.demo")
        hid = new_ticket(client, "detail-pages")
        expected = [
            user_message(client, hid, f"n1-page-{index}") for index in range(5)
        ]
        with factory.begin() as db:
            segment_id = db.scalar(select(SESSION_QUEUE_SEGMENTS.c.id).where(
                SESSION_QUEUE_SEGMENTS.c.session_id == hid,
                SESSION_QUEUE_SEGMENTS.c.queue_id == "n1",
            ))
            for i in range(4):
                row = SessionEvent(
                    session_id=hid, event_type="ACTIVE", actor=f"synthetic-{i}",
                )
                db.add(row)
                db.flush()
                db.execute(insert(SESSION_EVENT_QUEUE_PROVENANCE).values(
                    event_id=row.id,
                    segment_id=segment_id,
                    assigned_by="RUNTIME",
                    confidence="VERIFIED",
                ))

        transfer(client, factory, hid)
        user_message(client, hid, "N2-confidential-after-transfer")
        url = f"{BASE}/{hid}/verified-history"
        one = client.get(url, headers=auditor, params={
            "queue_id": "n1", "message_page": 1, "event_page": 1,
            "page_size": 2,
        })
        assert one.status_code == 200, one.text
        assert one.json()["partial_history"] is True
        assert one.json()["page_size"] == 2
        assert len(one.json()["messages"]) == 2
        assert len(one.json()["events"]) == 2
        assert one.json()["message_next_page"] == 2
        assert one.json()["event_next_page"] == 2
        assert "N2-confidential-after-transfer" not in one.text
        assert "reason" not in one.text

        # Advancing messages must not advance the event page.
        two = client.get(url, headers=auditor, params={
            "queue_id": "n1", "message_page": 2, "event_page": 1,
            "page_size": 2,
        })
        assert two.status_code == 200
        assert len(two.json()["messages"]) == 2
        assert two.json()["events"] == one.json()["events"]
        assert two.json()["message_next_page"] == 3

        three = client.get(url, headers=auditor, params={
            "queue_id": "n1", "message_page": 3, "event_page": 3,
            "page_size": 2,
        })
        assert three.status_code == 200
        assert len(three.json()["messages"]) == 1
        assert len(three.json()["events"]) == 2  # QUEUED + 4 ACTIVE + TRANSFERRED
        assert three.json()["message_next_page"] is None
        assert three.json()["event_next_page"] is None
        all_ids = [
            *(m["id"] for m in one.json()["messages"]),
            *(m["id"] for m in two.json()["messages"]),
            *(m["id"] for m in three.json()["messages"]),
        ]
        assert set(all_ids) == set(expected)
        assert len(all_ids) == len(expected)

        other_queue = client.get(url, headers=supervisor, params={
            "queue_id": "n2", "page_size": 2,
        })
        assert other_queue.status_code == 200
        assert [m["content"] for m in other_queue.json()["messages"]] == [
            "N2-confidential-after-transfer",
        ]
        assert "n1-page-" not in other_queue.text


def test_verified_detail_pages_revalidate_grant_and_reject_invalid_parameters(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        admin = bearer(client, passwords, "admin.demo")
        hid = new_ticket(client, "detail-grant")
        for i in range(3):
            user_message(client, hid, f"before-revoke-{i}")
        url = f"{BASE}/{hid}/verified-history"
        params = {"queue_id": "n1", "page_size": 2}
        first = client.get(url, headers=auditor, params=params)
        assert first.status_code == 200
        assert first.json()["message_next_page"] == 2
        assert client.get(url, headers=auditor, params={
            **params, "message_page": 0,
        }).status_code == 422
        assert client.get(url, headers=auditor, params={
            **params, "event_page": 1001,
        }).status_code == 422
        assert client.get(url, headers=auditor, params={
            **params, "page_size": 51,
        }).status_code == 422
        with factory() as db:
            uid = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "auditor.demo",
            ))
        revoke = client.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": uid, "queue_id": "n1",
            "role": "AUDITOR", "enabled": False,
        })
        assert revoke.status_code == 200
        assert client.get(url, headers=auditor, params={
            **params, "message_page": 2,
        }).status_code == 404


def test_unversioned_detail_with_page_options_keeps_history_closed(tmp_path):
    app, factory, passwords = environment(tmp_path, versioned=False)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "detail-unversioned")
        for i in range(3):
            user_message(client, hid, f"legacy-message-{i}")
        result = client.get(f"{BASE}/{hid}/verified-history", headers=auditor, params={
            "queue_id": "n1", "message_page": 2, "event_page": 2, "page_size": 1,
        })
        assert result.status_code == 404
    with factory() as db:
        tables = set(db.scalars(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).all())
        assert len(tables) == 17
        assert "session_queue_segments" not in tables


def test_verified_history_access_is_persistently_journaled_without_payloads(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "journal-content")
        user_message(client, hid, "SENSITIVE_MESSAGE_FOR_TEST")
        listed = verified_listing(client, "n1", auditor)
        assert listed.status_code == 200
        details = history(client, hid, "n1", auditor)
        assert details.status_code == 200
        assert "SENSITIVE_MESSAGE_FOR_TEST" in details.text
        with factory() as db:
            audit_rows = db.execute(
                select(HISTORY_ACCESS_AUDIT)
                .order_by(HISTORY_ACCESS_AUDIT.c.created_at, HISTORY_ACCESS_AUDIT.c.id)
            ).mappings().all()
            assert len(audit_rows) == 2
            assert {row["resource"] for row in audit_rows} == {"LIST", "DETAIL"}
            list_row = next(r for r in audit_rows if r["resource"] == "LIST")
            detail_row = next(r for r in audit_rows if r["resource"] == "DETAIL")
            assert list_row["user_id"] == detail_row["user_id"]
            assert list_row["role"] == "AUDITOR"
            assert list_row["operation_id"] == "demo"
            assert list_row["queue_id"] == "n1"
            assert list_row["session_id"] is None
            assert list_row["returned_sessions"] == 1
            assert detail_row["session_id"] == hid
            assert detail_row["message_page"] == 1
            assert detail_row["event_page"] == 1
            assert detail_row["returned_messages"] == 1
            assert detail_row["returned_events"] == 1
            assert "SENSITIVE_MESSAGE_FOR_TEST" not in str(audit_rows)
        # Denied cross-queue request does not make a successful read.
        assert history(client, hid, "n2", auditor).status_code == 404
        assert verified_listing(client, "n2", auditor).status_code == 404
        with factory() as db:
            assert len(db.execute(select(HISTORY_ACCESS_AUDIT)).all()) == 2
    # An auditable access cannot be destroyed by a routine schema downgrade.
    database = tmp_path / "verified.db"
    with pytest.raises(RuntimeError, match="Refusing destructive downgrade"):
        command.downgrade(_config(database), PROVENANCE_REVISION)
    state = verify_database(database)
    assert state["revision"] == AUDIT_REVISION
    assert state["row_counts"]["history_access_audit"] == 2


def test_audit_storage_failure_prevents_verified_payload_delivery(tmp_path):
    app, factory, passwords = environment(tmp_path)
    # This SQLite trigger models an unavailable journal WITHOUT deleting schema.
    with TestClient(app, raise_server_exceptions=False) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "audit-write-failed")
        user_message(client, hid, "DO_NOT_DISCLOSE_ON_AUDIT_FAILURE")
        with factory.begin() as db:
            db.connection().exec_driver_sql(
                "CREATE TRIGGER reject_audit_insert BEFORE INSERT ON history_access_audit "
                "BEGIN SELECT RAISE(ABORT, 'journal unavailable'); END"
            )
        listing = verified_listing(client, "n1", auditor)
        details = history(client, hid, "n1", auditor)
        assert listing.status_code == 500
        assert details.status_code == 500
        assert "DO_NOT_DISCLOSE_ON_AUDIT_FAILURE" not in listing.text
        assert "DO_NOT_DISCLOSE_ON_AUDIT_FAILURE" not in details.text
        with factory() as db:
            assert len(db.execute(select(HISTORY_ACCESS_AUDIT)).all()) == 0


def test_verified_data_stays_closed_on_versioned_database_without_audit_schema(tmp_path):
    database = tmp_path / "older-revision.db"
    create_new(database, confirmed=True)
    # Downgrade only an empty, disposable test database to model legacy 006B-2.
    command.downgrade(_config(database), PROVENANCE_REVISION)
    url = f"sqlite:///{database.as_posix()}"
    factory, engine = make_session_factory(url)
    credentials = tmp_path / "older-credentials.txt"
    provision(factory, credentials)
    passwords = {
        line.split(" [", 1)[0]: line.split("]: ", 1)[1]
        for line in credentials.read_text(encoding="utf-8").splitlines()
        if " [" in line and "]: " in line
    }
    engine.dispose()
    app = create_app(database_url=url, api_key="local-test-only")
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "older-audit-revision")
        user_message(client, hid, "CONFIDENTIAL_LEGACY_VERSIONED")
        listing = verified_listing(client, "n1", auditor)
        details = history(client, hid, "n1", auditor)
        assert listing.status_code == 503
        assert details.status_code == 503
        assert "CONFIDENTIAL_LEGACY_VERSIONED" not in details.text
    with factory() as db:
        tables = set(db.scalars(text(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )).all())
        assert "history_access_audit" not in tables
        assert "session_queue_segments" in tables


def test_security_denials_record_scoped_actions_without_hidden_identifiers(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        hid = new_ticket(client, "security-denials")
        user_message(client, hid, "DO_NOT_LOG_MESSAGE_CONTENT")
        assert history(client, hid, "n2", auditor).status_code == 404
        assert verified_listing(client, "n2", auditor).status_code == 404
        assert history(client, "foreign-session", "n1", auditor).status_code == 404
        assert verified_listing(client, "unknown-queue", auditor).status_code == 404
        with factory() as db:
            rows = db.execute(select(SECURITY_DECISIONS)).mappings().all()
            assert len(rows) == 4
            assert {r["action"] for r in rows} == {
                "HISTORY_LIST_DENIED", "HISTORY_DETAIL_DENIED",
            }
            assert all(r["actor_role"] == "AUDITOR" for r in rows)
            assert all(r["outcome"] == "DENIED" for r in rows)
            assert all(r["operation_id"] == "demo" for r in rows)
            assert [r["queue_id"] for r in rows].count(None) == 1
            assert "foreign-session" not in str(rows)
            assert "DO_NOT_LOG_MESSAGE_CONTENT" not in str(rows)
            assert "unknown-queue" not in str(rows)
            assert all(r["target_user_id"] is None for r in rows)


def test_security_grant_and_revocation_records_are_atomic_and_idempotent(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app) as client:
        admin = bearer(client, passwords, "admin.demo")
        auditor = bearer(client, passwords, "auditor.demo")
        with factory() as db:
            target = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "auditor.demo",
            ))
            actor = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "admin.demo",
            ))
        args = {"user_id": target, "queue_id": "n1", "role": "AUDITOR"}
        endpoint = "/v1/admin/queue-grants"
        disabled = client.patch(endpoint, headers=admin, json={
            **args, "enabled": False,
        })
        assert disabled.status_code == 200, disabled.text
        again = client.patch(endpoint, headers=admin, json={
            **args, "enabled": False,
        })
        assert again.status_code == 200
        # Scope denial after revocation does not restore old history access.
        assert verified_listing(client, "n1", auditor).status_code == 404
        enabled = client.patch(endpoint, headers=admin, json={
            **args, "enabled": True,
        })
        assert enabled.status_code == 200, enabled.text
        with factory() as db:
            rows = db.execute(select(SECURITY_DECISIONS)
                              .order_by(SECURITY_DECISIONS.c.created_at,
                                        SECURITY_DECISIONS.c.id)).mappings().all()
            assert len(rows) == 3
            grant_rows = [r for r in rows if r["outcome"] == "APPLIED"]
            assert {r["action"] for r in grant_rows} == {
                "GRANT_ENABLED", "GRANT_REVOKED",
            }
            assert len(grant_rows) == 2
            assert all(r["actor_user_id"] == actor for r in grant_rows)
            assert all(r["target_user_id"] == target for r in grant_rows)
            assert all(r["queue_id"] == "n1" for r in grant_rows)
            assert all(r["operation_id"] == "demo" for r in grant_rows)
            assert "GRANT_REVOKED" in {r["action"] for r in rows}


def test_security_journal_failure_cannot_commit_admin_grant(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        admin = bearer(client, passwords, "admin.demo")
        with factory.begin() as db:
            target = db.scalar(select(AuthUser.id).where(
                AuthUser.username == "auditor.demo",
            ))
            db.connection().exec_driver_sql(
                "CREATE TRIGGER block_security_write "
                "BEFORE INSERT ON security_decisions "
                "BEGIN SELECT RAISE(ABORT, 'journal unavailable'); END"
            )
        response = client.patch("/v1/admin/queue-grants", headers=admin, json={
            "user_id": target, "queue_id": "n1", "role": "AUDITOR",
            "enabled": False,
        })
        assert response.status_code == 500
        with factory() as db:
            from handoff_hub.poc_db import QueueRoleGrant

            assert db.get(QueueRoleGrant, (target, "n1", "AUDITOR")) is not None
            assert db.execute(select(SECURITY_DECISIONS)).all() == []


def test_failed_denial_audit_does_not_change_scoped_http_denial(tmp_path):
    app, factory, passwords = environment(tmp_path)
    with TestClient(app, raise_server_exceptions=False) as client:
        auditor = bearer(client, passwords, "auditor.demo")
        with factory.begin() as db:
            db.connection().exec_driver_sql(
                "CREATE TRIGGER block_security_write "
                "BEFORE INSERT ON security_decisions "
                "BEGIN SELECT RAISE(ABORT, 'journal unavailable'); END"
            )
        response = verified_listing(client, "n2", auditor)
        assert response.status_code == 404
        assert response.json()["detail"] == "Fila não encontrada"
        with factory() as db:
            assert db.execute(select(SECURITY_DECISIONS)).all() == []
