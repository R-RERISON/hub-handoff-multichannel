"""Generate missing audit evidence using only an attested 006b4 TEMP lab.

Requires --confirm-synthetic because POSTs and protected GETs write synthetic
handoffs, messages and audit journals. NEVER contacts the original POC SQLite;
a live API is consulted solely by GET /v1/auth/me with a TEMP-minted bearer.
The scenario's POSTs/GETs run through TestClient explicitly bound to TEMP.
No secrets, tokens, conversation IDs or message contents are printed.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app
from handoff_hub.schema_admin import SchemaSafetyError
from scripts.lab_environment import LabSafetyError, validate_lab
from scripts.release_audit_evidence import collect
from scripts.release_grant_toggle import (
    LabSafetyError as AttestationSafetyError,
    attest_running_backend,
    bearer,
    identities,
)

INTERNAL_QA_KEY = "release-audit-fixture-in-process-only"
SYNTHETIC_MESSAGE = "Mensagem sintetica de QA do diario 006b4"


def expect_status(actual: int, desired: int, checkpoint: str) -> None:
    if actual != desired:
        raise LabSafetyError(
            f"Cenario {checkpoint} falhou (HTTP {actual}, esperado {desired})"
        )


def run(lab_dir: str | Path, confirmed: bool) -> dict:
    if not confirmed:
        raise LabSafetyError("Use --confirm-synthetic para gerar evidencias no banco TEMP")
    lab = validate_lab(lab_dir)
    _, auditor_id = identities(lab.database)
    prior = collect(lab.directory)
    if not prior["auditor_has_n1"] or prior["auditor_has_n2"]:
        raise LabSafetyError(
            "Escopo AUDITOR inesperado; restaure somente N1 e mantenha N2 vedada"
        )

    # Explicit DB URL; no environmental HANDOFF_DB_URL or default database.
    app = create_app(database_url=lab.database_url, api_key=INTERNAL_QA_KEY)
    with TestClient(app, raise_server_exceptions=False) as client:
        auditor = bearer(client, lab.credentials, "auditor.demo", auditor_id)

        # Fail closed before any handoff/message/journal scenario write if the
        # live browser server is on another DB or is not available.
        attest_running_backend(auditor, auditor_id)

        scope = client.get("/v1/me/queues", headers=auditor)
        expect_status(scope.status_code, 200, "scope")
        granted = {item["id"] for item in scope.json()}
        if "n1" not in granted or "n2" in granted:
            raise LabSafetyError("Escopo da API sintetica nao corresponde ao esperado")

        unique = uuid4().hex
        synthetic = {"X-POC-Key": INTERNAL_QA_KEY}
        created = client.post(
            "/v1/handoffs",
            headers={**synthetic, "Idempotency-Key": "audit-release-" + unique},
            json={
                "operation_id": "demo",
                "integration_id": "demo-bot",
                "queue_id": "n1",
                "requester_label": "Solicitante sintetico QA",
                "subject": "Evidencia de auditoria sintetica 006b4",
                "external_conversation_id": "audit-release-" + unique,
            },
        )
        expect_status(created.status_code, 201, "synthetic_handoff")
        session_id = created.json()["id"]
        message = client.post(
            f"/v1/handoffs/{session_id}/messages",
            headers=synthetic,
            json={
                "sender": "USER",
                "content": SYNTHETIC_MESSAGE,
                "external_message_id": "audit-msg-" + unique,
            },
        )
        expect_status(message.status_code, 201, "synthetic_message")

        listing = client.get(
            "/v1/history/verified-sessions",
            params={"queue_id": "n1"}, headers=auditor,
        )
        expect_status(listing.status_code, 200, "authorized_list_n1")
        if not listing.json().get("schema_ready"):
            raise LabSafetyError("Listagem de segmentos verificados nao esta pronta")
        detail = client.get(
            f"/v1/handoffs/{session_id}/verified-history",
            params={"queue_id": "n1"}, headers=auditor,
        )
        expect_status(detail.status_code, 200, "authorized_detail_n1")
        payload = detail.json()
        if (
            payload.get("scope") != "RUNTIME_VERIFIED_QUEUE_ONLY"
            or not payload.get("partial_history")
            or SYNTHETIC_MESSAGE not in [m["content"] for m in payload["messages"]]
        ):
            raise LabSafetyError("Detalhe nao confirmou conteudo sintetico VERIFIED N1")

        denied_list = client.get(
            "/v1/history/verified-sessions",
            params={"queue_id": "n2"}, headers=auditor,
        )
        denied_detail = client.get(
            f"/v1/handoffs/{session_id}/verified-history",
            params={"queue_id": "n2"}, headers=auditor,
        )
        expect_status(denied_list.status_code, 404, "denied_list_n2")
        expect_status(denied_detail.status_code, 404, "denied_detail_n2")
        if (
            SYNTHETIC_MESSAGE in denied_list.text
            or SYNTHETIC_MESSAGE in denied_detail.text
            or session_id in denied_list.text
            or session_id in denied_detail.text
        ):
            raise LabSafetyError("Resposta negada revelou conteudo sintetico protegido")

    final = collect(lab.directory)
    delta_list = final["authorized_list_reads"] - prior["authorized_list_reads"]
    delta_detail = final["authorized_detail_reads"] - prior["authorized_detail_reads"]
    delta_denied = final["recorded_scoped_denials"] - prior["recorded_scoped_denials"]
    if delta_list < 1 or delta_detail < 1 or delta_denied < 2:
        raise LabSafetyError(
            "Diarios 006b4 nao registraram todas as leituras/negativas exigidas"
        )
    return {
        "result": "PASS",
        "scope": "TEMP_SYNTHETIC_006B4_ONLY",
        "live_api_attested": True,
        "synthetic_verified_session_created": True,
        "authorized_list_http": 200,
        "authorized_detail_http": 200,
        "cross_queue_list_http": 404,
        "cross_queue_detail_http": 404,
        "read_list_audits_added": delta_list,
        "read_detail_audits_added": delta_detail,
        "denied_decisions_added": delta_denied,
        "audit_release_result": final["result"],
        "remaining_audit_gates": final["pending"],
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True, help="Valid TEMP laboratory directory")
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.lab, args.confirm_synthetic)
    except (LabSafetyError, AttestationSafetyError) as exc:
        # Only static errors and numeric HTTP status codes are exposed.
        raise SystemExit("REPROVADO: " + str(exc)) from None
    except (SchemaSafetyError, OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        raise SystemExit(
            "REPROVADO: falha de laboratorio TEMP ou contrato de API sintetica"
        ) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
