"""Static guards for RC-001 Block 02 operational batch executor."""
from scripts import rc001_operational_gate as gate


def test_operational_runner_has_one_full_gate_and_both_targeted_suites():
    assert len(gate.BASELINE_SHA) == 40
    assert gate.REMOTE_REF == "origin/feat/rc001-operations-batch"
    assert "tests/test_rc001_operations_batch.py" in gate.OPERATION_TESTS
    assert "tests/test_spec007_queue_lifecycle.py" in gate.ADMIN_TESTS
    assert "tests/test_spec007_b1_people_inventory.py" in gate.ADMIN_TESTS


def test_operational_runner_never_uses_original_database():
    import inspect

    source = inspect.getsource(gate.main)
    assert '"--check"' in source
    assert '"--lab"' not in source
    assert '"candidate_rc_001_integrated": False' in source
    assert '"original_database_write_instrumentation": "NOT_PERFORMED"' in source
    assert '"g09_independent_review": "REQUIRED"' in source
