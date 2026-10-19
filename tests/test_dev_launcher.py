"""Launcher unit tests: no network, frontend or running background processes."""
from pathlib import Path

from scripts import dev


def test_fingerprint_changes_with_content(tmp_path: Path) -> None:
    file = tmp_path / "pyproject.toml"
    file.write_text("original", encoding="utf-8")
    first = dev.fingerprint([file])
    file.write_text("changed", encoding="utf-8")
    assert dev.fingerprint([file]) != first


def test_poc_key_is_persisted_locally(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("HANDOFF_POC_KEY", raising=False)
    monkeypatch.setattr(dev, "LOCAL_KEY_FILE", tmp_path / "data" / ".poc-key")
    first = dev.local_key()
    assert len(first) >= 32
    assert dev.local_key() == first
    assert (tmp_path / "data" / ".poc-key").read_text(encoding="utf-8").strip() == first


def test_explicit_key_has_precedence(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HANDOFF_POC_KEY", "test-injected-secret")
    monkeypatch.setattr(dev, "LOCAL_KEY_FILE", tmp_path / "data" / ".poc-key")
    assert dev.local_key() == "test-injected-secret"
    assert not (tmp_path / "data" / ".poc-key").exists()


def test_placeholder_is_not_used_as_a_secret(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HANDOFF_POC_KEY", "SUA-CHAVE-LOCAL-FORTE")
    monkeypatch.setattr(dev, "LOCAL_KEY_FILE", tmp_path / "data" / ".poc-key")
    generated = dev.local_key()
    assert generated != "SUA-CHAVE-LOCAL-FORTE"


def test_check_runs_all_local_gates(monkeypatch) -> None:
    commands: list[tuple[tuple[str, ...], Path, dict[str, str] | None]] = []
    monkeypatch.setenv("HANDOFF_DB_URL", "sqlite:///must-not-be-inherited.db")
    monkeypatch.setenv("HANDOFF_POC_KEY", "must-not-be-inherited")
    monkeypatch.setattr(dev, "ensure_dependencies", lambda: ("python", "npm"))

    def capture_command(args, cwd=dev.ROOT, env=None):
        commands.append((tuple(args), cwd, env))

    monkeypatch.setattr(dev, "run_command", capture_command)
    assert dev.main(["--check"]) == 0
    assert [(args, cwd) for args, cwd, _ in commands] == [
        (("python", "-m", "pytest", "-q"), dev.ROOT),
        (("python", "-m", "ruff", "check", "src", "tests"), dev.ROOT),
        (("npm", "run", "build"), dev.WEB),
    ]
    assert all(env is not None for _, _, env in commands)
    assert all("HANDOFF_DB_URL" not in env for _, _, env in commands)
    assert all("HANDOFF_POC_KEY" not in env for _, _, env in commands)


def test_setup_only_never_starts_services(monkeypatch) -> None:
    monkeypatch.setattr(dev, "ensure_dependencies", lambda: ("python", "npm"))

    def forbid(*_args, **_kwargs):
        raise AssertionError("start not expected")

    monkeypatch.setattr(dev, "spawn", forbid)
    assert dev.main(["--setup-only"]) == 0
