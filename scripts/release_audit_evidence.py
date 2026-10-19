"""Read-only release evidence for the disposable 006b4 browser laboratory.

No HTTP requests, passwords, login, tokens, identifiers or message text.
NEVER accepts data/handoff-poc.db; the lab MUST be a validated direct child
of the operating system's TEMP directory.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from handoff_hub.schema_admin import SchemaSafetyError
from scripts.lab_environment import LabSafetyError, validate_lab

AUDITOR = "auditor.demo"
N1 = "n1"
N2 = "n2"


def _readonly(database: Path) -> sqlite3.Connection:
    conn = sqlite3.connect(database.as_uri() + "?mode=ro", uri=True, timeout=10)
    conn.execute("PRAGMA query_only=ON")
    return conn


def collect(lab_dir: str | Path) -> dict:
    """Summarize only known, non-sensitive counters from a validated TEMP DB."""
    lab = validate_lab(lab_dir)
    with closing(_readonly(lab.database)) as db:
        row = db.execute(
            "SELECT id FROM auth_users WHERE username=? AND role='AUDITOR'",
            (AUDITOR,),
        ).fetchone()
        if row is None:
            raise LabSafetyError("Conta sintetica AUDITOR ausente ou com perfil invalido")
        auditor_id = row[0]
        active_n1 = db.execute(
            "SELECT count(*) FROM queue_role_grants "
            "WHERE user_id=? AND queue_id=? AND role='AUDITOR'",
            (auditor_id, N1),
        ).fetchone()[0] == 1
        exposed_n2 = db.execute(
            "SELECT count(*) FROM queue_role_grants "
            "WHERE user_id=? AND queue_id=? AND role='AUDITOR'",
            (auditor_id, N2),
        ).fetchone()[0] != 0
        transitions = [
            r[0] for r in db.execute(
                "SELECT action FROM security_decisions WHERE "
                "target_user_id=? AND queue_id=? AND actor_role='ADMIN' "
                "AND outcome='APPLIED' AND action IN ('GRANT_ENABLED','GRANT_REVOKED') "
                "ORDER BY created_at, id",
                (auditor_id, N1),
            )
        ]
        revoked = transitions.count("GRANT_REVOKED")
        restored = transitions.count("GRANT_ENABLED")
        cycle = any(
            left == "GRANT_REVOKED" and "GRANT_ENABLED" in transitions[i + 1:]
            for i, left in enumerate(transitions)
        )
        reads = dict(db.execute(
            "SELECT resource, count(*) FROM history_access_audit "
            "WHERE user_id=? AND queue_id=? AND role='AUDITOR' "
            "AND resource IN ('LIST','DETAIL') GROUP BY resource",
            (auditor_id, N1),
        ))
        denied = db.execute(
            "SELECT count(*) FROM security_decisions "
            "WHERE actor_user_id=? AND actor_role='AUDITOR' AND outcome='DENIED' "
            "AND action IN ('HISTORY_LIST_DENIED','HISTORY_DETAIL_DENIED')",
            (auditor_id,),
        ).fetchone()[0]

    # Independent acceptance gates: never claim a UX/browser verification from DB.
    journal = bool(cycle and revoked >= 1 and restored >= 1)
    read_gate = reads.get("LIST", 0) > 0 and reads.get("DETAIL", 0) > 0
    denial_gate = denied > 0
    scope_gate = active_n1 and not exposed_n2
    findings = []
    if not journal:
        findings.append("GRANT_CYCLE_NOT_PROVEN")
    if not scope_gate:
        findings.append("FINAL_AUDITOR_SCOPE_NOT_EXPECTED")
    if not read_gate:
        findings.append("VERIFIED_LIST_AND_DETAIL_READS_NOT_PROVEN")
    if not denial_gate:
        findings.append("SCOPED_ACCESS_DENIAL_NOT_PROVEN")
    return {
        "result": "PASS" if not findings else "INCOMPLETE",
        "database_scope": "TEMP_SYNTHETIC_006B4_READ_ONLY",
        "database_revision": "006b4_security_decisions",
        "security_grant_cycle": "PASS" if journal else "PENDING",
        "final_auditor_scope": "PASS" if scope_gate else "PENDING",
        "history_read_journal": "PASS" if read_gate else "PENDING",
        "denied_access_journal": "PASS" if denial_gate else "PENDING",
        "auditor_has_n1": active_n1,
        "auditor_has_n2": exposed_n2,
        "grant_revoke_events": revoked,
        "grant_restore_events": restored,
        "authorized_list_reads": reads.get("LIST", 0),
        "authorized_detail_reads": reads.get("DETAIL", 0),
        "recorded_scoped_denials": denied,
        "pending": findings,
        "database_changes": 0,
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True, help="Explicit TEMP 006b4 lab directory")
    args = parser.parse_args()
    try:
        result = collect(args.lab)
    except (LabSafetyError, SchemaSafetyError, OSError, sqlite3.Error, KeyError):
        # Do not disclose a path, user ID, SQL statement or file content.
        raise SystemExit(
            "REPROVADO: laboratorio TEMP invalido ou consulta de auditoria indisponivel"
        ) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if result["result"] != "PASS":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
