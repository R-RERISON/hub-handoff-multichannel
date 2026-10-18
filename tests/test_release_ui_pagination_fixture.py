"""TEMP-only browser pagination fixture contract and safety tests.

Never refers to, mounts, inspects, or modifies data/handoff-poc.db.
"""
import pytest
from sqlalchemy import func, select

from handoff_hub.poc_db import HandoffSession, Message, SessionEvent, make_session_factory
from scripts import lab_environment
from scripts import release_grant_toggle as toggle
from scripts import release_ui_pagination_fixture as fixture


def new_lab(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    return lab_environment.prepare_lab()


def counts(lab):
    factory, engine = make_session_factory(lab.database_url)
    try:
        with factory() as db:
            return (
                db.scalar(select(func.count()).select_from(HandoffSession)),
                db.scalar(select(func.count()).select_from(Message)),
                db.scalar(select(func.count()).select_from(SessionEvent)),
            )
    finally:
        engine.dispose()


def test_ux06_fixture_requires_explicit_consent(tmp_path, monkeypatch):
    lab = new_lab(tmp_path, monkeypatch)
    before = counts(lab)
    with pytest.raises(lab_environment.LabSafetyError, match="confirm-synthetic"):
        fixture.run(lab.directory, confirmed=False)
    assert counts(lab) == before == (0, 0, 0)


def test_ux06_fixture_fails_before_data_creation_if_live_db_is_not_attested(
    tmp_path, monkeypatch,
):
    lab = new_lab(tmp_path, monkeypatch)

    def deny(_headers, _expected_id):
        raise toggle.LabSafetyError("TEMP attestation failed")

    monkeypatch.setattr(fixture, "attest_running_backend", deny)
    with pytest.raises(toggle.LabSafetyError, match="TEMP attestation failed"):
        fixture.run(lab.directory, confirmed=True)
    assert counts(lab) == (0, 0, 0)


def test_ux06_fixture_generates_and_verifies_independent_page_two(
    tmp_path, monkeypatch,
):
    lab = new_lab(tmp_path, monkeypatch)
    monkeypatch.setattr(fixture, "attest_running_backend", lambda *_: None)
    report = fixture.run(lab.directory, confirmed=True)
    assert report["result"] == "PASS"
    assert report["scope"] == "TEMP_SYNTHETIC_006B4_ONLY"
    assert report["synthetic_sessions_added"] == 27
    assert report["synthetic_messages_added"] == 27
    assert report["synthetic_qa_events_added"] == 27
    assert report["verified_session_page_2"] == "AVAILABLE"
    assert report["verified_message_page_2"] == "AVAILABLE"
    assert report["verified_event_page_2"] == "AVAILABLE"
    assert report["independent_message_event_paging"] == "PASS"
    assert report["auditor_scope_unchanged"] is True
    assert report["original_database_touched"] is False
    assert "ui-pagination-" not in str(report)
    assert counts(lab) == (27, 27, 54)
