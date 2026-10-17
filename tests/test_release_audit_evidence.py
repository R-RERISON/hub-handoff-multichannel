"""Integration tests for read-only, TEMP-only release journal evidence.

These tests never resolve, inspect or mutate data/handoff-poc.db.
"""
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, make_session_factory
from scripts import lab_environment as environment
from scripts import release_audit_evidence as evidence


def synthetic_lab(tmp_path, monkeypatch):
    monkeypatch.setattr(environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return environment.prepare_lab()


def bearer(client, lab, username):
    prefix = username + " ["
    passwords = [
        line.split("]: ", 1)[1]
        for line in lab.credentials.read_text(encoding="utf-8").splitlines()
        if line.startswith(prefix) and "]: " in line
    ]
    assert len(passwords) == 1
    response = client.post("/v1/auth/login", json={
        "username": username, "password": passwords[0],
    })
    assert response.status_code == 200
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def test_report_rejects_any_directory_outside_valid_temp_lab(tmp_path, monkeypatch):
    lab = synthetic_lab(tmp_path, monkeypatch)
    unrelated = tmp_path / "other"
    unrelated.mkdir()
    try:
        evidence.collect(unrelated)
    except environment.LabSafetyError:
        pass
    else:
        raise AssertionError("Report accepted a non-006b4 TEMP path")
    assert evidence.collect(lab.directory)["original_database_touched"] is False


def test_report_is_incomplete_on_new_lab_and_never_modifies_data(tmp_path, monkeypatch):
    lab = synthetic_lab(tmp_path, monkeypatch)
    before = lab.database.read_bytes()
    report = evidence.collect(lab.directory)
    assert report["result"] == "INCOMPLETE"
    assert report["database_scope"] == "TEMP_SYNTHETIC_006B4_READ_ONLY"
    assert report["security_grant_cycle"] == "PENDING"
    assert report["history_read_journal"] == "PENDING"
    assert report["denied_access_journal"] == "PENDING"
    assert report["final_auditor_scope"] == "PASS"
    assert report["database_changes"] == 0
    assert lab.database.read_bytes() == before


def test_report_passes_actual_read_deny_revoke_restore_cycle(tmp_path, monkeypatch):
    lab = synthetic_lab(tmp_path, monkeypatch)
    app = create_app(database_url=lab.database_url, api_key="qa-local-synthetic-only")
    with TestClient(app) as client:
        auditor = bearer(client, lab, "auditor.demo")
        admin = bearer(client, lab, "admin.demo")
        created = client.post("/v1/handoffs", headers={
            "X-POC-Key": "qa-local-synthetic-only",
            "Idempotency-Key": "audit-qa-synthetic-1",
        }, json={
            "operation_id": "demo", "integration_id": "demo-bot",
            "queue_id": "n1", "requester_label": "Pessoa sintetica",
            "subject": "Teste de trilhas 006b4",
            "external_conversation_id": "audit-qa-synthetic",
        })
        assert created.status_code == 201
        hid = created.json()["id"]
        msg = client.post(f"/v1/handoffs/{hid}/messages", headers={
            "X-POC-Key": "qa-local-synthetic-only",
        }, json={
            "sender": "USER",
            "content": "Conteudo que NAO deve entrar na evidencia",
            "external_message_id": "audit-qa-msg",
        })
        assert msg.status_code == 201

        listing = client.get(
            "/v1/history/verified-sessions",
            params={"queue_id": "n1"}, headers=auditor,
        )
        assert listing.status_code == 200
        detail = client.get(
            f"/v1/handoffs/{hid}/verified-history",
            params={"queue_id": "n1"}, headers=auditor,
        )
        assert detail.status_code == 200

        denied = client.get(
            "/v1/history/verified-sessions",
            params={"queue_id": "n2"}, headers=auditor,
        )
        assert denied.status_code == 404

        factory, engine = make_session_factory(lab.database_url)
        try:
            with factory() as db:
                auditor_id = db.scalar(select(AuthUser.id).where(
                    AuthUser.username == "auditor.demo",
                ))
        finally:
            engine.dispose()
        for action in (False, True):
            change = client.patch(
                "/v1/admin/queue-grants",
                headers=admin,
                json={
                    "user_id": auditor_id, "queue_id": "n1",
                    "role": "AUDITOR", "enabled": action,
                },
            )
            assert change.status_code == 200

    before = lab.database.read_bytes()
    report = evidence.collect(lab.directory)
    assert report["result"] == "PASS"
    assert report["security_grant_cycle"] == "PASS"
    assert report["history_read_journal"] == "PASS"
    assert report["denied_access_journal"] == "PASS"
    assert report["final_auditor_scope"] == "PASS"
    assert report["authorized_list_reads"] >= 1
    assert report["authorized_detail_reads"] >= 1
    assert report["recorded_scoped_denials"] >= 1
    assert report["grant_revoke_events"] == 1
    assert report["grant_restore_events"] == 1
    assert report["auditor_has_n1"] is True
    assert report["auditor_has_n2"] is False
    assert "Conteudo que NAO deve entrar" not in str(report)
    assert report["pending"] == []
    assert lab.database.read_bytes() == before
