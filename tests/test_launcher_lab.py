"""One-command launcher and disposable QA lab isolation gates.

No test in this module opens or seeds data/handoff-poc.db.
"""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import dev, lab_environment as lab


def test_disposable_lab_is_created_and_reused_without_reset(tmp_path, monkeypatch):
    monkeypatch.setattr(lab.tempfile, "gettempdir", lambda: str(tmp_path))
    created = lab.prepare_lab()
    assert created.created is True
    assert created.database.is_file()
    assert created.credentials.is_file()
    original_credentials = created.credentials.read_bytes()
    original_bytes = created.database.stat().st_size
    from handoff_hub.schema_admin import SECURITY_REVISION, verify_database

    state = verify_database(created.database)
    assert state["revision"] == SECURITY_REVISION
    assert state["table_count"] == 22
    assert state["row_counts"]["auth_users"] == 5

    resumed = lab.validate_lab(created.directory)
    assert resumed.created is False
    assert resumed.database_url == created.database_url
    assert resumed.credentials.read_bytes() == original_credentials
    assert resumed.database.stat().st_size == original_bytes


def test_lab_refuses_non_temp_directories_and_dangling_files(tmp_path, monkeypatch):
    monkeypatch.setattr(lab.tempfile, "gettempdir", lambda: str(tmp_path))
    unrelated = tmp_path / "data"
    unrelated.mkdir()
    with pytest.raises(lab.LabSafetyError, match="dedicated"):
        lab.validate_lab(unrelated)

    uninitialized = tmp_path / "handoff-qa-006b4-not-seeded"
    uninitialized.mkdir()
    with pytest.raises(lab.LabSafetyError, match="missing or linked"):
        lab.validate_lab(uninitialized)


def test_lab_rejects_symlink_to_any_external_database(tmp_path, monkeypatch):
    monkeypatch.setattr(lab.tempfile, "gettempdir", lambda: str(tmp_path))
    labdir = tmp_path / "handoff-qa-006b4-symlink-attempt"
    labdir.mkdir()
    other = tmp_path / "external.db"
    other.write_bytes(b"never modify")
    try:
        (labdir / "synthetic.db").symlink_to(other)
    except (OSError, NotImplementedError):
        pytest.skip("Symlink creation unsupported in this Windows environment")
    (labdir / "synthetic-credentials.txt").write_text("synthetic", encoding="utf-8")
    with pytest.raises(lab.LabSafetyError, match="linked outside"):
        lab.validate_lab(labdir)
    assert other.read_bytes() == b"never modify"


def test_launcher_uses_installed_venv_to_prepare_temp_lab(monkeypatch):
    expected = {
        "directory": "TEMP/handoff-qa-006b4-test",
        "database_url": "sqlite:///TEMP/handoff-qa-006b4-test/synthetic.db",
        "credentials": "TEMP/handoff-qa-006b4-test/synthetic-credentials.txt",
        "created": True,
    }
    calls = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(stdout=json.dumps(expected))

    monkeypatch.setattr(dev.subprocess, "run", fake_run)
    info = dev.prepare_lab_from_venv("python-from-venv", None)
    assert info == expected
    assert calls[0][0] == [
        "python-from-venv", "-m", "scripts.lab_environment", "create",
    ]

    dev.prepare_lab_from_venv("python-from-venv", "TEMP/handoff-qa-006b4-test")
    assert calls[1][0] == [
        "python-from-venv", "-m", "scripts.lab_environment",
        "resume", "--lab-dir", "TEMP/handoff-qa-006b4-test",
    ]


def test_start_lab_spawns_both_services_without_touching_original(tmp_path, monkeypatch):
    monkeypatch.setattr(dev, "ensure_dependencies", lambda: ("python-venv", "npm.cmd"))
    monkeypatch.setattr(dev, "port_in_use", lambda port: False)
    url = f"sqlite:///{(tmp_path / 'synthetic.db').as_posix()}"
    monkeypatch.setattr(dev, "prepare_lab_from_venv", lambda python, path: {
        "directory": str(tmp_path), "database_url": url,
        "credentials": str(tmp_path / "synthetic-credentials.txt"), "created": True,
    })
    spawned = []

    def fake_spawn(label, cmd, cwd, env):
        spawned.append((label, cmd, cwd, env.copy()))
        return object()

    def stop_at_ready(_children):
        raise KeyboardInterrupt

    monkeypatch.setattr(dev, "spawn", fake_spawn)
    monkeypatch.setattr(dev, "wait_for_services", stop_at_ready)
    monkeypatch.setattr(dev, "stop_children", lambda children: None)
    monkeypatch.setattr(
        dev, "run_command",
        lambda *a, **k: pytest.fail("Lab launch must not seed default POC"),
    )
    monkeypatch.setattr(dev.webbrowser, "open", lambda *_: pytest.fail("Browser disabled"))
    assert dev.main(["--lab", "--no-browser"]) == 0
    assert [p[0] for p in spawned] == ["API", "WEB"]
    assert all(p[3]["HANDOFF_DB_URL"] == url for p in spawned)
    assert all("HANDOFF_POC_KEY" not in p[3] for p in spawned)
    assert "--reload" not in spawned[0][1]


def test_default_launcher_ignores_inherited_custom_database(tmp_path, monkeypatch):
    monkeypatch.setenv("HANDOFF_DB_URL", f"sqlite:///{(tmp_path / 'elsewhere.db').as_posix()}")
    monkeypatch.setenv("HANDOFF_POC_KEY", "should-not-reach-backend")
    monkeypatch.setattr(dev, "ensure_dependencies", lambda: ("python-venv", "npm.cmd"))
    monkeypatch.setattr(dev, "port_in_use", lambda port: False)
    seeded = []
    spawned = []
    monkeypatch.setattr(
        dev, "run_command",
        lambda cmd, **kwargs: seeded.append((cmd, kwargs["env"].copy())),
    )
    monkeypatch.setattr(
        dev, "spawn",
        lambda label, cmd, cwd, env: spawned.append((cmd, env.copy())) or object(),
    )

    def stop_at_ready(_children):
        raise KeyboardInterrupt

    monkeypatch.setattr(dev, "wait_for_services", stop_at_ready)
    monkeypatch.setattr(dev, "stop_children", lambda _: None)
    assert dev.main(["--no-browser"]) == 0
    assert len(seeded) == 1
    assert "HANDOFF_DB_URL" not in seeded[0][1]
    assert "HANDOFF_DB_URL" not in spawned[0][1]
    assert "--reload" in spawned[0][0]
    assert Path(dev.ROOT / "data" / "handoff-poc.db") != tmp_path / "elsewhere.db"
