"""RC-001 Block 02: single Windows G01/G04/G06/G07 operational QA batch.

Only ephemeral in-process test databases. No browser passwords, runtime POC
database access, CI, automated merge, or production deployment.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

from scripts.rc001_integrated_gate import execute, run_git, unsafe_changed_files

ROOT = Path(__file__).resolve().parents[1]
BASELINE_SHA = "20ff982444310ef5c7dbce15d9d208ee0c1724b0"
REMOTE_REF = "origin/feat/rc001-operations-batch"
OPERATION_TESTS = (
    "tests/test_rc001_operations_batch.py",
    "tests/test_operator_workflow.py",
    "tests/test_queue_scopes.py",
    "tests/test_runtime_provenance.py",
    "tests/test_default_intake.py",
    "tests/test_state_machine.py",
)
ADMIN_TESTS = (
    "tests/test_spec007_queue_create.py",
    "tests/test_spec007_queue_lifecycle.py",
    "tests/test_spec007_b1_people_inventory.py",
    "tests/test_spec007_admin_inventory.py",
    "tests/test_spec007_people_boundaries.py",
    "tests/test_launcher_lab.py",
)


def verify(expected_sha: str) -> dict:
    if os.name != "nt":
        raise ValueError("Windows-only integrated gate.")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise ValueError("Full 40-character expected SHA is mandatory.")
    if os.environ.get("HANDOFF_DB_URL"):
        raise ValueError("HANDOFF_DB_URL must be unset.")
    if not ROOT.name.lower().startswith("handoff-rc001-operations-"):
        raise ValueError("Use a dedicated handoff-rc001-operations-* QA worktree.")
    if not os.path.samefile(ROOT.parent, Path(tempfile.gettempdir())):
        raise ValueError("QA worktree must be a direct child of OS TEMP.")
    if run_git("rev-parse", "HEAD") != expected_sha:
        raise ValueError("Local HEAD mismatch.")
    if run_git("rev-parse", "--verify", REMOTE_REF) != expected_sha:
        raise ValueError("Fetched remote branch mismatch.")
    if run_git("status", "--porcelain"):
        raise ValueError("QA worktree contains changes.")
    if run_git("rev-parse", "--verify",
               "origin/integration/rc-001-consolidated-poc-20261019") != BASELINE_SHA:
        raise ValueError("RC-001 frozen SHA changed.")
    touched = run_git("diff", "--name-only", BASELINE_SHA, expected_sha).splitlines()
    if unsafe_changed_files(touched):
        raise ValueError("Review sensitive paths in the candidate diff.")
    return {"sha": expected_sha, "baseline_sha": BASELINE_SHA,
            "changed_file_count": len(touched)}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    try:
        verified = verify(args.expected_sha)
    except (OSError, RuntimeError, ValueError):
        print("BLOCKED: QA checkout or revision prerequisites not satisfied.",
              file=sys.stderr)
        return 2

    evidence_dir = Path(tempfile.mkdtemp(prefix="handoff-rc001-operations-evidence-"))
    output = evidence_dir / "summary.json"
    summary = {
        "schema": "RC001_OPERATIONS_BATCH_V1",
        "run_utc": datetime.now(UTC).isoformat(),
        **verified,
        "steps": [], "automated_result": "NOT_RUN",
        "g04_g06_manual_browser_review": "REQUIRED",
        "g07_browser_zoom_retest": "REQUIRED",
        "g09_independent_review": "REQUIRED",
        "g10_formal_acceptance": "REQUIRED",
        "original_database_write_instrumentation": "NOT_PERFORMED",
        "candidate_rc_001_integrated": False,
    }
    py = str(ROOT / ".venv" / "Scripts" / "python.exe")
    stages = (
        ("G01_FULL", ["cmd.exe", "/D", "/C", str(ROOT / "start.cmd"), "--check"]),
        ("G04_N1_N2_FLOW", [py, "-m", "pytest", "-q", *OPERATION_TESTS]),
        ("G06_QUEUE_PEOPLE", [py, "-m", "pytest", "-q", *ADMIN_TESTS]),
        ("G07_FRONTEND_ARCH", ["cmd.exe", "/D", "/C", "node", "--test",
                                "web/scripts/workspaces.test.mjs"]),
        ("RELEASE_PROBE", [py, "scripts/release_probe.py"]),
    )
    for name, command in stages:
        if name != "G01_FULL" and name != "G07_FRONTEND_ARCH" and not Path(py).is_file():
            result = {"gate": name, "result": "BLOCKED", "exit_code": None}
        else:
            result = execute(name, command)
        summary["steps"].append(result)
        if result["result"] != "PASS":
            summary["automated_result"] = "BLOCKED"
            break
    else:
        summary["automated_result"] = "PASS"
    output.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")
    print("Sanitized evidence: " + str(output))
    print("AUTOMATED " + summary["automated_result"])
    return 0 if summary["automated_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
