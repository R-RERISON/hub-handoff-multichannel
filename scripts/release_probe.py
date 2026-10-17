"""Release-gate smoke check against an EPHEMERAL SQLite, never data/handoff-poc.db.

Run: .venv\\Scripts\\python.exe scripts/release_probe.py
Creates its own temporary 006b4 database and credentials, exercises real
FastAPI bearer authorization with TestClient, then removes all temporary data.
No live server, no original DB, no network and no GitHub Actions.
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from tempfile import TemporaryDirectory

from fastapi.testclient import TestClient
from sqlalchemy import select

from handoff_hub.audit_schema import HISTORY_ACCESS_AUDIT
from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import AuthUser, QueueRoleGrant, make_session_factory
from handoff_hub.schema_admin import SECURITY_REVISION, create_new, verify_database
from handoff_hub.security_schema import SECURITY_DECISIONS
from handoff_hub.seed_demo_auth import provision

# Failed negative audit persistence is expected in the injected-fault test.
logging.getLogger("handoff.security").setLevel(logging.CRITICAL)

KEY = {"X-POC-Key": "synthetic-api-client-only"}
EXPECTED_ACTIONS = {
    "HISTORY_LIST_DENIED", "GRANT_REVOKED", "GRANT_ENABLED",
}


def check(condition: bool, message: str) -> None:
    if not condition:
        raise AssertionError(message)


def login(client: TestClient, credentials: dict[str, str], name: str) -> dict:
    response = client.post("/v1/auth/login", json={
        "username": name, "password": credentials[name],
    })
    check(response.status_code == 200, f"{name}: bearer login not available")
    return {"Authorization": "Bearer " + response.json()["access_token"]}


def run_probe(root: Path) -> dict:
    database = root / "release-only.db"
    create_new(database, confirmed=True)
    url = f"sqlite:///{database.as_posix()}"
    factory, engine = make_session_factory(url)
    credential_path = root / "release-only-credentials.txt"
    try:
        provision(factory, credential_path)
        credentials = {
            line.split(" [", 1)[0]: line.split("]: ", 1)[1]
            for line in credential_path.read_text(encoding="utf-8").splitlines()
            if " [" in line and "]: " in line
        }
        app = create_app(database_url=url, api_key=KEY["X-POC-Key"])
        with TestClient(app, raise_server_exceptions=False) as client:
            admin = login(client, credentials, "admin.demo")
            auditor = login(client, credentials, "auditor.demo")
            created = client.post(
                "/v1/handoffs",
                headers={**KEY, "Idempotency-Key": "release-probe-1"},
                json={
                    "operation_id": "demo",
                    "integration_id": "demo-bot",
                    "queue_id": "n1",
                    "external_conversation_id": "release-synthetic",
                    "requester_label": "Synthetic User",
                    "subject": "Release-gate synthetic item",
                },
            )
            check(created.status_code == 201, "Synthetic intake failed")
            session = created.json()["id"]
            marker = "SYNTHETIC_SECRET_NEVER_IN_AUDIT"
            posted = client.post(f"/v1/handoffs/{session}/messages", headers=KEY, json={
                "sender": "USER",
                "content": marker,
                "external_message_id": "release-message",
            })
            check(posted.status_code == 201, "Synthetic message failed")

            list_url = "/v1/history/verified-sessions"
            details_url = f"/v1/handoffs/{session}/verified-history"
            ok_list = client.get(list_url, params={"queue_id": "n1"}, headers=auditor)
            check(ok_list.status_code == 200, "Verified list denied for granted auditor")
            check(ok_list.json()["schema_ready"] is True, "006b4 not audit ready")
            check(len(ok_list.json()["tickets"]) == 1, "Expected verified session missing")
            details = client.get(details_url, params={
                "queue_id": "n1",
            }, headers=auditor)
            check(details.status_code == 200, "Verified detail denied for granted auditor")
            check(marker in details.text, "Verified message missing from own scope")

            denied = client.get(list_url, params={"queue_id": "n2"}, headers=auditor)
            check(denied.status_code == 404, "Cross-queue list was not denied")
            check(marker not in denied.text, "Denied list contained private message")

            with factory() as db:
                target = db.scalar(select(AuthUser.id).where(
                    AuthUser.username == "auditor.demo",
                ))
            check(bool(target), "Target user not found")
            change = {
                "user_id": target, "queue_id": "n1",
                "role": "AUDITOR", "enabled": False,
            }
            revoked = client.patch("/v1/admin/queue-grants", headers=admin, json=change)
            check(revoked.status_code == 200, "Admin revoke failed")
            after_revoke = client.get(list_url, params={
                "queue_id": "n1",
            }, headers=auditor)
            check(after_revoke.status_code == 404, "Grant revocation did not take effect")
            restored = client.patch("/v1/admin/queue-grants", headers=admin, json={
                **change, "enabled": True,
            })
            check(restored.status_code == 200, "Admin restoration failed")

            with factory() as db:
                reads = db.execute(select(HISTORY_ACCESS_AUDIT)).mappings().all()
                decisions = db.execute(select(SECURITY_DECISIONS)).mappings().all()
                check(len(reads) == 2, "Unexpected successful-read journal count")
                check(len(decisions) == 4, "Unexpected security journal count")
                check({r["action"] for r in decisions} == EXPECTED_ACTIONS,
                      "Missing security decision action")
                check(all(r["operation_id"] == "demo" for r in decisions),
                      "Unexpected journal operation")
                check(all(r["actor_user_id"] for r in decisions), "Actor not recorded")
                check(all(marker not in str(row) for row in (*reads, *decisions)),
                      "Sensitive message content persisted to a journal")

            # Inject an INSERT failure. Grant restoration MUST remain committed;
            # attempted revocation MUST roll back as audit cannot be persisted.
            with factory.begin() as db:
                db.connection().exec_driver_sql(
                    "CREATE TRIGGER reject_release_audit "
                    "BEFORE INSERT ON security_decisions "
                    "BEGIN SELECT RAISE(ABORT, 'audit store unavailable'); END"
                )
            failed_change = client.patch(
                "/v1/admin/queue-grants", headers=admin, json=change,
            )
            check(failed_change.status_code == 500,
                  "Grant change succeeded without mandatory audit write")
            with factory() as db:
                check(db.get(QueueRoleGrant, (target, "n1", "AUDITOR")) is not None,
                      "Grant was mutated despite failed audit write")
            failed_denial = client.get(list_url, params={
                "queue_id": "n2",
            }, headers=auditor)
            check(failed_denial.status_code == 404,
                  "Audit failure changed a denied request to another status")
            check(marker not in failed_denial.text, "Audit failure exposed content")

        state = verify_database(database)
        check(state["revision"] == SECURITY_REVISION,
              "Unexpected disposable database revision")
        check(state["table_count"] == 22,
              "Expected 17 baseline + 3 provenance + 2 audit tables")
        check(state["row_counts"]["history_access_audit"] == 2,
              "Read journal was not durable")
        check(state["row_counts"]["security_decisions"] == 4,
              "Security decision journal was not durable")
        return {
            "result": "PASS",
            "database_scope": "EPHEMERAL_SYNTHETIC_ONLY",
            "database_revision": SECURITY_REVISION,
            "table_count": state["table_count"],
            "successful_read_audits": state["row_counts"]["history_access_audit"],
            "security_decisions": state["row_counts"]["security_decisions"],
            "rbac_cross_queue": "DENIED",
            "grant_revocation": "ENFORCED",
            "audit_failure_during_grant": "ROLLED_BACK",
            "audit_failure_during_denial": "PRESERVED_404",
            "sensitive_payload_in_journals": False,
        }
    finally:
        engine.dispose()


def main() -> None:
    with TemporaryDirectory(prefix="handoff-main-gate-") as temporary:
        result = run_probe(Path(temporary))
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
