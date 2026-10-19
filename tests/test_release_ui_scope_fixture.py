"""Safety and behavior tests for the SPEC-006C TEMP-only scope fixture."""
import sqlite3

import pytest
from sqlalchemy import func, select

from handoff_hub.poc_db import HandoffSession, Message, make_session_factory
from scripts import lab_environment
from scripts import release_ui_scope_fixture as fixture


def lab_for(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def totals(lab):
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            return (
                db.scalar(select(func.count()).select_from(HandoffSession)),
                db.scalar(select(func.count()).select_from(Message)),
            )
    finally:
        engine.dispose()


def test_requires_confirmation_before_any_write(tmp_path, monkeypatch):
    lab = lab_for(tmp_path, monkeypatch)
    with pytest.raises(lab_environment.LabSafetyError, match="confirm-synthetic"):
        fixture.run(lab.directory, confirmed=False)
    assert totals(lab) == (0, 0)


def test_wrong_live_backend_fails_closed(tmp_path, monkeypatch):
    lab = lab_for(tmp_path, monkeypatch)

    def reject(*_):
        raise lab_environment.LabSafetyError("API diferente do laboratorio TEMP")

    monkeypatch.setattr(fixture, "attest_running_backend", reject)
    with pytest.raises(lab_environment.LabSafetyError, match="TEMP"):
        fixture.run(lab.directory, confirmed=True)
    assert totals(lab) == (0, 0)


def test_scope_mismatch_prevents_creating_any_session(tmp_path, monkeypatch):
    lab = lab_for(tmp_path, monkeypatch)
    with sqlite3.connect(lab.database) as db:
        db.execute(
            "DELETE FROM queue_role_grants WHERE queue_id='n2' "
            "AND role='SUPERVISOR'"
        )
    monkeypatch.setattr(fixture, "attest_running_backend", lambda *_: None)
    with pytest.raises(lab_environment.LabSafetyError, match="SUPERVISOR"):
        fixture.run(lab.directory, confirmed=True)
    assert totals(lab) == (0, 0)


def test_n1_n2_verified_transfer_and_negative_permissions(tmp_path, monkeypatch):
    lab = lab_for(tmp_path, monkeypatch)
    monkeypatch.setattr(fixture, "attest_running_backend", lambda *_: None)
    result = fixture.run(lab.directory, confirmed=True)
    assert result["result"] == "PASS"
    assert result["ux02_backend_scope"] == "PASS"
    assert result["ux05_backend_verified_isolation"] == "PASS"
    assert result["ux05_n2_operator_ready"] == "PASS"
    assert result["auditor_n2_http"] == 404
    assert result["supervisor_operator_write_http"] == 403
    assert result["private_note_exposed"] is False
    assert result["manual_ux02"] == "NOT_RUN"
    assert result["manual_ux05"] == "NOT_RUN"
    assert result["manual_ux08"] == "BLOCKED"
    assert result["original_database_touched"] is False
    assert totals(lab) == (1, 2)
    for secret in (fixture.N1_TEXT, fixture.N2_TEXT, fixture.PRIVATE_NOTE):
        assert secret not in str(result)
