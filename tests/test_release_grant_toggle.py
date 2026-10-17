"""TEMP-only QA grant CLI: attest the browser API before any grant mutation.

These tests create disposable 006b4 databases; the real POC SQLite is never
inspected, provisioned, migrated or modified by this suite.
"""
import sqlite3
from contextlib import closing

import pytest
from sqlalchemy import select

from handoff_hub.poc_db import AuthUser, make_session_factory
from handoff_hub.schema_admin import create_new
from handoff_hub.security_schema import SECURITY_DECISIONS
from handoff_hub.seed_demo_auth import provision
from scripts import release_grant_toggle as qa


def qa_lab(tmp_path, monkeypatch):
    monkeypatch.setattr(qa.tempfile, "gettempdir", lambda: str(tmp_path))
    lab = tmp_path / "handoff-qa-006b4-synthetic-only"
    lab.mkdir()
    path = lab / "synthetic.db"
    create_new(path, confirmed=True)
    factory, engine = make_session_factory(f"sqlite:///{path.as_posix()}")
    try:
        provision(factory, lab / "synthetic-credentials.txt")
    finally:
        engine.dispose()
    return lab, path, factory


def test_release_grant_cli_refuses_paths_outside_dedicated_temp_lab(tmp_path):
    another = tmp_path / "my-production-data"
    another.mkdir()
    with pytest.raises(qa.LabSafetyError):
        qa.lab_files(str(another))


def test_release_grant_cli_requires_live_api_attestation_before_revocation(
    tmp_path, monkeypatch,
):
    lab, path, factory = qa_lab(tmp_path, monkeypatch)

    def reject(_headers, _expected_id):
        raise qa.LabSafetyError("Running API did not accept TEMP bearer")

    monkeypatch.setattr(qa, "attest_running_backend", reject)
    with pytest.raises(qa.LabSafetyError, match="did not accept"):
        qa.run(str(lab), "revoke", confirmed=True)

    with factory() as db:
        target = db.scalar(select(AuthUser.id).where(
            AuthUser.username == "auditor.demo",
        ))
        assert qa.count_grants(path, target) == 1
        assert db.execute(select(SECURITY_DECISIONS)).all() == []


def test_release_grant_cli_revoke_restore_only_in_temp_and_journals_changes(
    tmp_path, monkeypatch,
):
    lab, path, factory = qa_lab(tmp_path, monkeypatch)

    def accepted(headers, expected_id):
        assert headers["Authorization"].startswith("Bearer ")
        with closing(sqlite3.connect(
            path.resolve().as_uri() + "?mode=ro", uri=True,
        )) as conn:
            assert conn.execute(
                "SELECT count(*) FROM auth_users WHERE id=?", (expected_id,),
            ).fetchone()[0] == 1

    monkeypatch.setattr(qa, "attest_running_backend", accepted)
    revoked = qa.run(str(lab), "revoke", confirmed=True)
    assert revoked["result"] == "PASS"
    assert revoked["auditor_has_n1"] is False
    assert revoked["grant_events_added"] == 1

    # Repeated revoke is idempotent, not a second security event.
    repeated = qa.run(str(lab), "revoke", confirmed=True)
    assert repeated["grant_events_added"] == 0

    restored = qa.run(str(lab), "restore", confirmed=True)
    assert restored["auditor_has_n1"] is True
    assert restored["grant_events_added"] == 1
    assert restored["original_database_touched"] is False
    with factory() as db:
        rows = db.execute(select(SECURITY_DECISIONS)).mappings().all()
        assert len(rows) == 2
        assert {r["action"] for r in rows} == {"GRANT_REVOKED", "GRANT_ENABLED"}


def test_release_grant_attestation_denies_unrecognized_live_server(monkeypatch):
    class FakeResponse:
        status_code = 401

    class FakeClient:
        def __init__(self, *args, **kwargs):
            assert kwargs["trust_env"] is False
            assert kwargs["base_url"] == qa.API

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback):
            return False

        def get(self, url, headers):
            assert url == "/v1/auth/me"
            assert headers["Authorization"] == "Bearer TEMP_ONLY"
            return FakeResponse()

    monkeypatch.setattr(qa.httpx, "Client", FakeClient)
    with pytest.raises(qa.LabSafetyError, match="nao reconhece"):
        qa.attest_running_backend(
            {"Authorization": "Bearer TEMP_ONLY"}, "synthetic-account",
        )
