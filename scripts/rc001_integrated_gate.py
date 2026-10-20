"""RC-001 integrated Windows regression: G00/G01/G02/G05/G08, G09 input only.

One invocation runs the existing full gate, scoped security/persona/audit suites,
and the ephemeral release probe. Never opens a POC database, contacts the
production services, logs credentials, or marks independent review/user acceptance as PASS.
No GitHub Actions are used.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RC_SHA = "20ff982444310ef5c7dbce15d9d208ee0c1724b0"
REMOTE_REF = "origin/feat/rc001-security-audit-batch"
TARGETED_RBAC = (
    "tests/test_rc001_persona_matrix.py",
    "tests/test_rbac_auto_dispatch.py",
    "tests/test_queue_scopes.py",
    "tests/test_spec007_people_boundaries.py",
    "tests/test_spec007_b1_people_inventory.py",
    "tests/test_spec007_admin_inventory.py",
    "tests/test_release_grant_toggle.py",
)
TARGETED_AUDIT = (
    "tests/test_verified_history.py",
    "tests/test_release_audit_evidence.py",
    "tests/test_release_audit_scenarios.py",
    "tests/test_release_ui_evidence_gate.py",
)
FORBIDDEN_SUFFIXES = (".db", ".sqlite", ".sqlite3", ".pem", ".p12", ".pfx", ".key")


class GateSafetyError(RuntimeError):
    """Fixed diagnostic suitable for sanitized output."""


def run_git(*args: str) -> str:
    call = subprocess.run(
        ["git", *args], cwd=ROOT, text=True, encoding="utf-8",
        errors="replace", capture_output=True, check=False,
    )
    if call.returncode != 0:
        raise GateSafetyError("Git verification failed; no tests were started.")
    return call.stdout.strip()


def unsafe_changed_files(paths: list[str]) -> list[str]:
    """Reject paths associated with runtime state or nonexample secrets."""
    unsafe = []
    for path in paths:
        normalized = path.replace("\\", "/").lower()
        parts = normalized.split("/")
        if (normalized.startswith("data/") or normalized.startswith(".git/")
                or normalized.endswith(FORBIDDEN_SUFFIXES)
                or any(part in {".env", "secrets", "credentials", "private_key"}
                       or (part.startswith(".env.") and part != ".env.example")
                       for part in parts)):
            unsafe.append(path)
    return unsafe


def preflight(expected_sha: str) -> dict:
    if os.name != "nt":
        raise GateSafetyError("This consolidated runner is Windows-only.")
    if not re.fullmatch(r"[0-9a-f]{40}", expected_sha):
        raise GateSafetyError("Expected SHA must be a full 40-character hex digest.")
    if os.environ.get("HANDOFF_DB_URL"):
        raise GateSafetyError("HANDOFF_DB_URL is set; remove it before QA.")
    if not ROOT.is_dir() or not (ROOT / "start.cmd").is_file():
        raise GateSafetyError("Invalid RC-001 checkout.")
    if not ROOT.name.lower().startswith("handoff-rc001-security-"):
        raise GateSafetyError("Use a dedicated handoff-rc001-security-* TEMP worktree.")
    # os.path.samefile is robust to Windows 8.3 aliases and long-path spellings.
    if not os.path.samefile(ROOT.parent, Path(tempfile.gettempdir())):
        raise GateSafetyError("Checkout is not a direct child of OS TEMP.")
    if run_git("rev-parse", "HEAD") != expected_sha:
        raise GateSafetyError("Local HEAD does not match expected SHA.")
    if run_git("rev-parse", "--verify", REMOTE_REF) != expected_sha:
        raise GateSafetyError("Fetched remote ref differs from expected SHA.")
    if run_git("status", "--porcelain"):
        raise GateSafetyError("Worktree has changes. Refusing destructive or ambiguous QA.")
    touched = run_git("diff", "--name-only", RC_SHA, expected_sha).splitlines()
    unsafe = unsafe_changed_files(touched)
    if unsafe:
        raise GateSafetyError("Diff includes runtime data or secret-like files; review required.")
    return {"sha": expected_sha, "rc_sha": RC_SHA, "changed_files": touched}


def pytest_counts(output: str) -> dict[str, int]:
    """Only aggregate test counters may survive into the local evidence JSON."""
    result = {}
    for key in ("passed", "failed", "skipped", "errors"):
        matches = re.findall(r"\b(\d+)\s+" + key + r"\b", output)
        if matches:
            result[key] = int(matches[-1])
    return result


def execute(label: str, args: list[str]) -> dict:
    print(f"[{label}] Running isolated gate...", flush=True)
    try:
        result = subprocess.run(
            args, cwd=ROOT, text=True, encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
            check=False, timeout=1800,
        )
        stdout = result.stdout or ""
        outcome = {
            "gate": label, "result": "PASS" if result.returncode == 0 else "FAIL",
            "exit_code": result.returncode, "pytest_counts": pytest_counts(stdout),
        }
    except subprocess.TimeoutExpired:
        outcome = {"gate": label, "result": "TIMEOUT", "exit_code": None}
    except OSError:
        outcome = {"gate": label, "result": "BLOCKED", "exit_code": None}
    print(f"[{label}] {outcome['result']}", flush=True)
    return outcome


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expected-sha", required=True)
    args = parser.parse_args()
    try:
        pre = preflight(args.expected_sha)
    except (GateSafetyError, OSError) as exc:
        print(f"PRECHECK BLOCKED: {exc}", file=sys.stderr)
        return 2

    evidence_dir = Path(tempfile.mkdtemp(prefix="handoff-rc001-batch-evidence-"))
    evidence_file = evidence_dir / "summary.json"
    summary: dict = {
        "schema": "RC001_BATCH_QA_V1",
        "run_utc": datetime.now(UTC).isoformat(),
        "sha": pre["sha"], "rc_baseline_sha": pre["rc_sha"],
        "source": "LOCAL_WINDOWS_SYNTHETIC_TESTS",
        "steps": [],
        "changed_file_count": len(pre["changed_files"]),
        "prohibited_path_patterns_detected": False,
        "raw_logs_or_credentials_saved_to_evidence": False,
        "original_database_write_instrumentation": "NOT_PERFORMED",
        "automated_result": "NOT_RUN",
        "g09_independent_review": "REQUIRED",
        "g10_human_acceptance": "REQUIRED",
        "live_browser_persona_audit_review": "REQUIRED",
        "candidate_rc_001_integrated": False,
    }
    python = str(ROOT / ".venv" / "Scripts" / "python.exe")
    stages = (
        ("G01_FULL_REGRESSION", ["cmd.exe", "/D", "/C", str(ROOT / "start.cmd"), "--check"]),
        ("G02_G05_ROLE_MATRIX", [python, "-m", "pytest", "-q", *TARGETED_RBAC]),
        ("G08_AUDIT_EVIDENCE", [python, "-m", "pytest", "-q", *TARGETED_AUDIT]),
        ("G02_G08_RELEASE_PROBE", [python, "scripts/release_probe.py"]),
    )
    for name, command in stages:
        if name != "G01_FULL_REGRESSION" and not Path(python).is_file():
            outcome = {"gate": name, "result": "BLOCKED", "exit_code": None}
        else:
            outcome = execute(name, command)
        summary["steps"].append(outcome)
        if outcome["result"] != "PASS":
            summary["automated_result"] = "BLOCKED"
            break
    else:
        summary["automated_result"] = "PASS"
    # Contains only fixed gate names and aggregate counts; no raw subprocess logs,
    # authentication data, SQLite backups, bearer tokens, IDs or chat text.
    evidence_file.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print("Sanitized evidence: " + str(evidence_file), flush=True)
    print("AUTOMATED " + summary["automated_result"], flush=True)
    return 0 if summary["automated_result"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
