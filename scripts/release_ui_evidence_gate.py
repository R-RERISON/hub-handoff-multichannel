"""SPEC-006C — read-only review of manual browser screenshots tied to a SHA.

This is NOT a visual test: verified screenshot dimensions and file hashes only.
Human reviewer must inspect sensitive content, identity and actual behavior.
No PASS/release decision is ever returned by this tool.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import struct
import subprocess
from pathlib import Path

from scripts.lab_environment import LabSafetyError, validate_lab

ROOT = Path(__file__).resolve().parents[1]
SIZES = ((390, 844), (1366, 768), (1920, 1080))
SHA_PATTERN = re.compile(r"^[a-f0-9]{40}$")
PNG_SIGNATURE = bytes.fromhex("89504e470d0a1a0a")
EVIDENCE_FOLDER = "qa-evidence"

REQUIRED = tuple(
    (f"UX-08", persona, area, "", width, height)
    for (width, height) in SIZES
    for persona, area in (("AUDITOR", "historico"), ("OPERATOR", "mesa"))
) + (
    ("UX-02", "SUPERVISOR", "historico", "n1", 1366, 768),
    ("UX-02", "SUPERVISOR", "historico", "n2", 1366, 768),
    ("UX-05", "SUPERVISOR", "historico", "n1", 1366, 768),
    ("UX-05", "SUPERVISOR", "historico", "n2", 1366, 768),
    ("UX-05", "OPERATOR", "mesa", "n2", 1366, 768),
)


def current_sha() -> str:
    try:
        outcome = subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"], cwd=ROOT,
            capture_output=True, text=True, timeout=10, check=True,
        )
    except (OSError, subprocess.SubprocessError):
        raise LabSafetyError("Nao foi possivel identificar o commit Git local") from None
    value = outcome.stdout.strip().lower()
    if not SHA_PATTERN.fullmatch(value):
        raise LabSafetyError("SHA do repositorio local invalido")
    return value


def slot(entry: dict) -> tuple:
    try:
        return (
            entry["gate"], entry["persona"], entry["area"], entry["queue"],
            entry["width"], entry["height"],
        )
    except (KeyError, TypeError):
        raise LabSafetyError("Metadados obrigatorios de captura ausentes") from None


def _safe_folder(lab: Path) -> Path:
    directory = lab / EVIDENCE_FOLDER
    if directory.is_symlink():
        raise LabSafetyError("Diretorio QA nao pode ser symlink")
    if directory.exists() and (not directory.is_dir()
                               or directory.resolve() != directory):
        raise LabSafetyError("Diretorio de evidencias QA inseguro")
    return directory


def initialize(lab_dir: str | Path) -> dict:
    lab = validate_lab(lab_dir)
    target = _safe_folder(lab.directory)
    if target.exists():
        if (target / "manifest.json").exists():
            raise LabSafetyError("Manifesto ja existe; nenhuma sobrescrita permitida")
    else:
        target.mkdir(mode=0o700)
    shots = []
    for index, (gate, persona, area, queue, width, height) in enumerate(REQUIRED, 1):
        name = f"{index:02d}_{gate.replace('-', '')}_{persona}_{area}_{queue or 'all'}_{width}x{height}.png"
        shots.append({
            "gate": gate, "persona": persona, "area": area, "queue": queue,
            "width": width, "height": height, "file": name,
        })
    output = {"schema_version": 1, "source_sha": current_sha(),
              "screenshots": shots}
    # Exclusive creation: do not overwrite evidence already collected.
    with (target / "manifest.json").open("x", encoding="utf-8") as fp:
        json.dump(output, fp, indent=2, ensure_ascii=False)
    return {
        "result": "TEMPLATE_CREATED",
        "expected_screenshots": len(shots),
        "source_sha": output["source_sha"],
        "captures_received": 0,
        "manual_review": "NOT_RUN",
        "original_database_touched": False,
    }


def _file_digest(path: Path, expected: tuple[int, int]) -> str:
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 15_000_000:
        raise LabSafetyError("Arquivo de captura invalido, grande ou com symlink")
    with path.open("rb") as fp:
        header = fp.read(24)
    if (len(header) != 24 or header[:8] != PNG_SIGNATURE
            or header[12:16] != b"IHDR"):
        raise LabSafetyError("Captura deve ser PNG valido com header IHDR")
    actual = struct.unpack(">II", header[16:24])
    if actual != expected:
        raise LabSafetyError("Dimensao PNG nao corresponde ao viewport declarado")
    digest = hashlib.sha256()
    with path.open("rb") as fp:
        for part in iter(lambda: fp.read(131072), b""):
            digest.update(part)
    return digest.hexdigest()


def inspect(lab_dir: str | Path) -> dict:
    lab = validate_lab(lab_dir)
    evidence = _safe_folder(lab.directory)
    manifest_path = evidence / "manifest.json"
    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise LabSafetyError("Manifesto de evidencias ausente ou inseguro")
    if manifest_path.stat().st_size > 100_000:
        raise LabSafetyError("Manifesto acima do limite")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (UnicodeError, ValueError):
        raise LabSafetyError("Manifesto JSON invalido") from None

    sha = current_sha()
    if manifest.get("schema_version") != 1 or manifest.get("source_sha") != sha:
        raise LabSafetyError("Manifesto nao corresponde ao SHA de codigo atual")

    observed = set()
    missing = []
    digests = set()
    required_set = set(REQUIRED)
    items = manifest.get("screenshots")
    if not isinstance(items, list) or len(items) != len(REQUIRED):
        raise LabSafetyError("Manifesto com quantidade incorreta de capturas")
    for item in items:
        if not isinstance(item, dict):
            raise LabSafetyError("Metadados de captura invalidos")
        key = slot(item)
        if key not in required_set or key in observed:
            raise LabSafetyError("Captura duplicada ou cenario desconhecido")
        observed.add(key)
        name = item.get("file")
        if (not isinstance(name, str) or not name.endswith(".png")
                or Path(name).name != name or name in (".", "..")
                or "/" in name or "\\" in name):
            raise LabSafetyError("Nome de captura nao permitido")
        path = evidence / name
        if not path.exists():
            missing.append((key[0], key[1], key[2], key[3], key[4], key[5]))
            continue
        digest = _file_digest(path, (key[4], key[5]))
        if digest in digests:
            raise LabSafetyError("Mesma imagem foi reutilizada em dois cenarios")
        digests.add(digest)
    if observed != required_set:
        raise LabSafetyError("Checklist nao corresponde aos casos UX exigidos")
    return {
        "result": "EVIDENCE_READY_FOR_MANUAL_REVIEW" if not missing else "INCOMPLETE",
        "source_sha": sha,
        "required_captures": len(REQUIRED),
        "present_captures": len(digests),
        "missing_captures": len(missing),
        "pending_slots": [
            {"gate": k[0], "persona": k[1], "area": k[2],
             "queue": k[3], "width": k[4], "height": k[5]}
            for k in missing
        ],
        "human_identity_review": "NOT_RUN",
        "human_privacy_review": "NOT_RUN",
        "human_behavior_review": "NOT_RUN",
        "release_approved": False,
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--init", action="store_true")
    selection.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        outcome = initialize(args.lab) if args.init else inspect(args.lab)
    except (LabSafetyError, OSError, ValueError, TypeError, KeyError):
        raise SystemExit("REPROVADO: evidencia QA ausente, inconsistente ou insegura") from None
    print(json.dumps(outcome, indent=2, ensure_ascii=False))
    if outcome["result"] == "INCOMPLETE":
        raise SystemExit(2)


if __name__ == "__main__":
    main()
