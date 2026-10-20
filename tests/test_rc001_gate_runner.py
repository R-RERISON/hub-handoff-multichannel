"""Security/robustness checks for the single-shot QA runner (no commands run)."""
from __future__ import annotations

import pytest

from scripts.rc001_integrated_gate import pytest_counts, unsafe_changed_files


@pytest.mark.parametrize("path", [
    "data/handoff-poc.db",
    "data/backups/release.sqlite",
    ".env",
    "web/.env",
    "web/.env.local",
    "secrets/token.txt",
    "deploy/private_key",
    "certificates/production.pfx",
])
def test_diff_guard_rejects_sensitive_or_runtime_paths(path):
    assert unsafe_changed_files([path]) == [path]


@pytest.mark.parametrize("path", [
    "src/handoff_hub/security_writer.py",
    "tests/test_rc001_persona_matrix.py",
    "docs/qa/RC-001-SECURITY-AUDIT-BATCH.md",
    ".env.example",
])
def test_diff_guard_accepts_code_tests_and_example_config(path):
    assert unsafe_changed_files([path]) == []


def test_parser_preserves_only_aggregate_counts():
    output = "private message was confidential\n= 174 passed, 1 skipped in 2.34s =\n"
    assert pytest_counts(output) == {"passed": 174, "skipped": 1}
    assert "confidential" not in str(pytest_counts(output))


def test_runner_names_require_explicit_source_revision():
    from scripts import rc001_integrated_gate as gate
    assert len(gate.RC_SHA) == 40
    assert gate.REMOTE_REF == "origin/feat/rc001-security-audit-batch"
    assert "tests/test_rc001_persona_matrix.py" in gate.TARGETED_RBAC
    assert "tests/test_verified_history.py" in gate.TARGETED_AUDIT
