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
    commands: list[tuple[tuple[str, ...], Path]] = []
    monkeypatch.setattr(dev, "ensure_dependencies", lambda: ("python", "npm"))
    monkeypatch.setattr(
        dev, "run_command",
        lambda args, cwd=dev.ROOT: commands.append((tuple(args), cwd)),
    )
    assert dev.main(["--check"]) == 0
    assert commands == [
        (("python", "-m", "pytest", "-q"), dev.ROOT),
        (("python", "-m", "ruff", "check", "src", "tests"), dev.ROOT),
        (("npm", "run", "build"), dev.WEB),
    ]


def test_setup_only_never_starts_services(monkeypatch) -> None:
    monkeypatch.setattr(dev, "ensure_dependencies", lambda: ("python", "npm"))

    def forbid(*_args, **_kwargs):
        raise AssertionError("start not expected")

    monkeypatch.setattr(dev, "spawn", forbid)
    assert dev.main(["--setup-only"]) == 0
