"""SPEC-006C screenshot evidence validation: never approves UX automatically."""
import json
import struct
import zlib
from pathlib import Path

import pytest

from scripts import lab_environment
from scripts import release_ui_evidence_gate as gate

SHA = "a" * 40


def setup(tmp_path, monkeypatch):
    monkeypatch.setattr(lab_environment.tempfile, "gettempdir", lambda: str(tmp_path))
    monkeypatch.setattr(gate, "current_sha", lambda: SHA)
    return lab_environment.prepare_lab()


def fake_png(path: Path, width: int, height: int, salt: int):
    """Create a structurally valid synthetic image; it proves NO visual behavior."""
    def chunk(name, payload):
        value = zlib.crc32(name + payload) & 0xffffffff
        return struct.pack(">I", len(payload)) + name + payload + struct.pack(">I", value)

    scanline = b"\x00" + bytes((salt, 0, 0)) * width
    path.write_bytes(
        gate.PNG_SIGNATURE
        + chunk(b"IHDR", struct.pack(">II", width, height) + bytes((8, 2, 0, 0, 0)))
        + chunk(b"IDAT", zlib.compress(scanline * height, level=6))
        + chunk(b"IEND", b"")
    )


def test_template_incomplete_and_never_release(tmp_path, monkeypatch):
    lab = setup(tmp_path, monkeypatch)
    result = gate.initialize(lab.directory)
    assert result["expected_screenshots"] == 11
    assert gate.inspect(lab.directory)["result"] == "INCOMPLETE"
    assert gate.inspect(lab.directory)["release_approved"] is False
    assert gate.inspect(lab.directory)["missing_captures"] == 11
    with pytest.raises(lab_environment.LabSafetyError, match="sobrescrita"):
        gate.initialize(lab.directory)


def test_rejects_different_commit_and_path_escape(tmp_path, monkeypatch):
    lab = setup(tmp_path, monkeypatch)
    gate.initialize(lab.directory)
    manifest = lab.directory / "qa-evidence" / "manifest.json"
    data = json.loads(manifest.read_text(encoding="utf-8"))
    data["source_sha"] = "b" * 40
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(lab_environment.LabSafetyError, match="SHA"):
        gate.inspect(lab.directory)
    data["source_sha"] = SHA
    data["screenshots"][0]["file"] = "../synthetic-credentials.txt"
    manifest.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(lab_environment.LabSafetyError, match="Nome"):
        gate.inspect(lab.directory)


def test_screenshots_match_exact_pixel_dimensions_and_stay_unapproved(
    tmp_path, monkeypatch,
):
    lab = setup(tmp_path, monkeypatch)
    gate.initialize(lab.directory)
    target = lab.directory / "qa-evidence"
    manifest = json.loads((target / "manifest.json").read_text(encoding="utf-8"))
    for i, shot in enumerate(manifest["screenshots"], 1):
        fake_png(target / shot["file"], shot["width"], shot["height"], i)
    result = gate.inspect(lab.directory)
    assert result["result"] == "EVIDENCE_READY_FOR_MANUAL_REVIEW"
    assert result["present_captures"] == 11
    assert result["missing_captures"] == 0
    assert result["human_behavior_review"] == "NOT_RUN"
    assert result["release_approved"] is False
    assert result["original_database_touched"] is False
    sample = manifest["screenshots"][0]
    fake_png(target / sample["file"], 999, 844, 35)
    with pytest.raises(lab_environment.LabSafetyError, match="Dimensao"):
        gate.inspect(lab.directory)
