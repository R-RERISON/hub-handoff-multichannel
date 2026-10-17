"""Explicit N1 auditor grant toggler for a TEMP 006b4 browser lab only.

Never uses the original POC SQLite. Never prints credentials, access tokens,
user IDs or request bodies. This is a manual browser-QA helper, not a production
administration command.

Example (PowerShell; API TEMP running on 127.0.0.1:8000):
  python scripts/release_grant_toggle.py --lab "$env:TEMP/handoff-qa-006b4-..." --action revoke --confirm-synthetic
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path

import httpx
from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app
from handoff_hub.schema_admin import SECURITY_REVISION, verify_database

API = "http://127.0.0.1:8000"
QUEUE = "n1"
TARGET = "auditor.demo"
ADMIN = "admin.demo"


class LabSafetyError(RuntimeError):
    """Refuse to write unless the target is the explicitly selected QA lab."""


def lab_files(raw: str) -> tuple[Path, Path]:
    lab = Path(raw).resolve(strict=True)
    temporary_root = Path(tempfile.gettempdir()).resolve()
    if (
        not lab.is_dir()
        or lab.parent != temporary_root
        or not lab.name.startswith("handoff-qa-006b4-")
    ):
        raise LabSafetyError("Lab must be a dedicated handoff-qa-006b4-* TEMP directory")
    db_path = lab / "synthetic.db"
    credentials = lab / "synthetic-credentials.txt"
    if not db_path.is_file() or not credentials.is_file():
        raise LabSafetyError("Synthetic database or local QA credentials not found")
    state = verify_database(db_path)
    if state["integrity"] != "ok" or state["revision"] != SECURITY_REVISION:
        raise LabSafetyError("Only a verified disposable 006b4 SQLite is eligible")
    return db_path, credentials


def identities(db_path: Path) -> tuple[str, str]:
    with closing(sqlite3.connect(
        db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10,
    )) as conn:
        accounts = dict(conn.execute(
            "SELECT username, id FROM auth_users WHERE username IN (?, ?)",
            (ADMIN, TARGET),
        ).fetchall())
    if ADMIN not in accounts or TARGET not in accounts:
        raise LabSafetyError("Expected synthetic ADMIN/AUDITOR accounts missing")
    return accounts[ADMIN], accounts[TARGET]


def password(path: Path, username: str) -> str:
    matches = [
        line.split("]: ", 1)[1]
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.startswith(username + " [") and "]: " in line
    ]
    if len(matches) != 1:
        raise LabSafetyError("Synthetic credentials incomplete for requested account")
    return matches[0]


def bearer(client: TestClient, credentials: Path, username: str,
           expected_id: str) -> dict[str, str]:
    response = client.post("/v1/auth/login", json={
        "username": username, "password": password(credentials, username),
    })
    if response.status_code != 200:
        raise LabSafetyError(
            "Lab credentials rejected; verify the running API uses the TEMP SQLite"
        )
    payload = response.json()
    if payload.get("user", {}).get("id") != expected_id:
        raise LabSafetyError("Running API user identity differs from the TEMP lab")
    return {"Authorization": "Bearer " + payload["access_token"]}


def count_grants(db_path: Path, target_id: str) -> int:
    with closing(sqlite3.connect(
        db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10,
    )) as conn:
        return int(conn.execute(
            "SELECT count(*) FROM queue_role_grants "
            "WHERE user_id=? AND queue_id=? AND role='AUDITOR'",
            (target_id, QUEUE),
        ).fetchone()[0])


def count_events(db_path: Path, target_id: str, action: str) -> int:
    with closing(sqlite3.connect(
        db_path.resolve().as_uri() + "?mode=ro", uri=True, timeout=10,
    )) as conn:
        return int(conn.execute(
            "SELECT count(*) FROM security_decisions "
            "WHERE target_user_id=? AND queue_id=? AND action=? AND outcome='APPLIED'",
            (target_id, QUEUE, action),
        ).fetchone()[0])


def attest_running_backend(headers: dict[str, str], expected_id: str) -> None:
    """Only READ the live API; never try a password or PATCH against an unknown DB.

    The bearer is minted *in the chosen temporary SQLite* via TestClient.
    An unrelated localhost server cannot validate it, even if it has the
    same synthetic usernames. All mutations happen via TestClient against
    the explicit temporary db_path, never via the live server.
    """
    try:
        with httpx.Client(base_url=API, timeout=6, trust_env=False) as live:
            response = live.get("/v1/auth/me", headers=headers)
    except httpx.ConnectError as exc:
        raise LabSafetyError(
            "API local indisponivel na porta 8000; inicie o run-backend.ps1 "
            "do laboratorio TEMP antes do teste"
        ) from exc
    except httpx.HTTPError as exc:
        raise LabSafetyError(
            "Nao foi possivel consultar /v1/auth/me no servidor local"
        ) from exc
    if response.status_code != 200:
        raise LabSafetyError(
            "API local nao reconhece a sessao do SQLite sintetico; "
            "confirme que run-backend.ps1 aponta para este mesmo laboratorio"
        )
    try:
        identity = response.json()
    except ValueError as exc:
        raise LabSafetyError("API local retornou perfil invalido") from exc
    if (
        identity.get("id") != expected_id
        or identity.get("username") != TARGET
        or identity.get("role") != "AUDITOR"
    ):
        raise LabSafetyError(
            "Identidade da API local nao corresponde ao banco de laboratorio"
        )


def run(lab: str, action: str, confirmed: bool) -> dict:
    db_path, credentials = lab_files(lab)
    if action != "status" and not confirmed:
        raise LabSafetyError("Use --confirm-synthetic to change TEMP grants")
    admin_id, target_id = identities(db_path)
    expected_grant = action == "restore"
    before = count_grants(db_path, target_id)
    event_type = "GRANT_ENABLED" if expected_grant else "GRANT_REVOKED"
    earlier_events = count_events(db_path, target_id, event_type)

    # Login and PATCH are bound explicitly to the verified TEMP database.
    # A different process on port 8000 can never receive passwords or grants.
    url = f"sqlite:///{db_path.as_posix()}"
    app = create_app(database_url=url, api_key="isolated-grant-qa-only")
    with TestClient(app, raise_server_exceptions=False) as local:
        admin = bearer(local, credentials, ADMIN, admin_id)
        auditor = bearer(local, credentials, TARGET, target_id)

        # Assert the browser's API uses this SAME temp DB before any PATCH.
        # Failed attestation sends only a temporary bearer via a READ request.
        attest_running_backend(auditor, target_id)

        if action != "status":
            response = local.patch("/v1/admin/queue-grants", headers=admin, json={
                "user_id": target_id,
                "queue_id": QUEUE,
                "role": "AUDITOR",
                "enabled": expected_grant,
            })
            if response.status_code != 200:
                raise LabSafetyError(
                    "TEMP grant operation rejected with HTTP " + str(response.status_code)
                )
        grants = local.get("/v1/me/queues", headers=auditor)
        if grants.status_code != 200:
            raise LabSafetyError("Cannot verify current auditor queue scope in TEMP")
        has_n1 = QUEUE in {q["id"] for q in grants.json()}
        after = count_grants(db_path, target_id)

    if after not in (0, 1) or has_n1 != bool(after):
        raise LabSafetyError("API and synthetic SQLite disagree about auditor scope")
    new_events = count_events(db_path, target_id, event_type)
    if action != "status":
        if has_n1 != expected_grant:
            raise LabSafetyError("Grant action did not take effect")
        expected_increment = 1 if bool(before) != expected_grant else 0
        if new_events != earlier_events + expected_increment:
            raise LabSafetyError("Security journal did not record the grant transition")

    return {
        "result": "PASS",
        "lab_scope": "TEMP_SYNTHETIC_006B4",
        "action": action.upper(),
        "queue": QUEUE,
        "role": "AUDITOR",
        "auditor_has_n1": has_n1,
        "grant_events_added": new_events - earlier_events,
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True, help="Dedicated TEMP lab directory")
    parser.add_argument("--action", required=True, choices=("status", "revoke", "restore"))
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.lab, args.action, args.confirm_synthetic)
    except LabSafetyError as exc:
        # Only purpose-built, static diagnostics: no tokens, passwords or DB IDs.
        raise SystemExit("REPROVADO: " + str(exc)) from None
    except (OSError, sqlite3.Error, httpx.HTTPError):
        raise SystemExit(
            "REPROVADO: falha de arquivo, SQLite ou rede no laboratorio sintetico"
        ) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
