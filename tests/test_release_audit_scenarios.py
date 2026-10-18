"""Reproducible 006b4 audit fixtures, strictly confined to TEMP SQLite.

These tests never discover, open, adopt or seed data/handoff-poc.db.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, HandoffSession, make_session_factory
from scripts import lab_environment
from scripts import release_audit_evidence as evidence
from scripts import release_audit_scenarios as scenarios
from scripts import release_grant_toggle as toggle


def lab(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def count_sessions(lab_state):
    factory, engine = make_session_factory(lab_state.database_url)
    try:
        with factory() as db:
            return len(db.scalars(select(HandoffSession.id)).all())
    finally:
        engine.dispose()


def test_scenario_requires_confirmation_and_never_uses_default_db(tmp_path, monkeypatch):
    target = lab(tmp_path, monkeypatch)
    with pytest.raises(lab_environment.LabSafetyError, match="confirm-synthetic"):
        scenarios.run(target.directory, confirmed=False)
    assert count_sessions(target) == 0
    assert evidence.collect(target.directory)["history_read_journal"] == "PENDING"


def test_attestation_failure_stops_before_any_synthetic_handoff_or_audit(
    tmp_path, monkeypatch,
):
    target = lab(tmp_path, monkeypatch)

    def deny(_headers, _expected_id):
        raise toggle.LabSafetyError("No live TEMP backend detected")

    monkeypatch.setattr(scenarios, "attest_running_backend", deny)
    with pytest.raises(toggle.LabSafetyError, match="No live TEMP"):
        scenarios.run(target.directory, confirmed=True)
    assert count_sessions(target) == 0
    state = evidence.collect(target.directory)
    assert state["authorized_list_reads"] == 0
    assert state["authorized_detail_reads"] == 0
    assert state["recorded_scoped_denials"] == 0


def test_integration_records_real_verified_reads_and_cross_queue_404(
    tmp_path, monkeypatch,
):
    target = lab(tmp_path, monkeypatch)
    monkeypatch.setattr(scenarios, "attest_running_backend", lambda *_: None)
    before = evidence.collect(target.directory)
    assert before["result"] == "INCOMPLETE"

    outcome = scenarios.run(target.directory, confirmed=True)
    assert outcome["result"] == "PASS"
    assert outcome["live_api_attested"] is True
    assert outcome["authorized_list_http"] == 200
    assert outcome["authorized_detail_http"] == 200
    assert outcome["cross_queue_list_http"] == 404
    assert outcome["cross_queue_detail_http"] == 404
    assert outcome["read_list_audits_added"] >= 1
    assert outcome["read_detail_audits_added"] >= 1
    assert outcome["denied_decisions_added"] >= 2
    assert outcome["audit_release_result"] == "INCOMPLETE"
    assert outcome["remaining_audit_gates"] == ["GRANT_CYCLE_NOT_PROVEN"]
    assert outcome["original_database_touched"] is False
    assert "Mensagem sintetica" not in str(outcome)

    after = evidence.collect(target.directory)
    assert after["history_read_journal"] == "PASS"
    assert after["denied_access_journal"] == "PASS"
    assert after["security_grant_cycle"] == "PENDING"
    assert after["final_auditor_scope"] == "PASS"
    assert count_sessions(target) == 1


def test_full_release_report_passes_after_genuine_grant_cycle_and_audit_scenario(
    tmp_path, monkeypatch,
):
    target = lab(tmp_path, monkeypatch)
    monkeypatch.setattr(scenarios, "attest_running_backend", lambda *_: None)

    app = create_app(database_url=target.database_url, api_key="qa-admin-temporary")
    with TestClient(app) as client:
        factory, engine = make_session_factory(target.database_url)
        try:
            with factory() as db:
                auditor_id = db.scalar(select(AuthUser.id).where(
                    AuthUser.username == "auditor.demo",
                ))
        finally:
            engine.dispose()
        admin = toggle.bearer(
            client, target.credentials, "admin.demo",
            toggle.identities(target.database)[0],
        )
        for enabled in (False, True):
            response = client.patch(
                "/v1/admin/queue-grants",
                headers=admin,
                json={
                    "user_id": auditor_id,
                    "queue_id": "n1",
                    "role": "AUDITOR",
                    "enabled": enabled,
                },
            )
            assert response.status_code == 200

    outcome = scenarios.run(target.directory, confirmed=True)
    assert outcome["audit_release_result"] == "PASS"
    assert outcome["remaining_audit_gates"] == []
    report = evidence.collect(target.directory)
    assert report["result"] == "PASS"
    assert report["grant_revoke_events"] == 1
    assert report["grant_restore_events"] == 1
    assert report["original_database_touched"] is False
