"""Prepare deterministic, disposable pagination data for PR #28 browser QA.

This module MUST only write to an attested 006b4 handoff-qa-* directory
directly under TEMP. Its data is entirely synthetic; no business data,
credentials, tokens, user IDs, session IDs or message bodies are printed.

It creates 27 verified N1 sessions, a focus session with 27 synthetic
messages, and 27 explicitly marked QA_PAGE_EVENT events. These synthetic
events use the same provenance writer as the application but are NOT
operational transitions; they exist solely to test UI event pagination.

The live API is only contacted by authenticated GET /v1/auth/me after
creating a temporary bearer in the selected SQLite. All writes use a
TestClient explicitly bound to the verified TEMP database.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import HandoffSession, SessionEvent, make_session_factory
from handoff_hub.provenance_writer import ProvenanceRecorder
from handoff_hub.schema_admin import SchemaSafetyError
from scripts.lab_environment import LabSafetyError, validate_lab
from scripts.release_grant_toggle import (
    LabSafetyError as AttestationSafetyError,
    attest_running_backend,
    bearer,
    identities,
)

LOCAL_KEY = "release-ui-fixture-testclient-only"
COUNT = 27
MARKER = "QA_PAGE_EVENT"


def require(status: int, expected: int, stage: str) -> None:
    if status != expected:
        raise LabSafetyError(
            f"Preparacao sintetica falhou em {stage}: HTTP {status} (esperado {expected})"
        )


def run(lab_dir: str | Path, confirmed: bool) -> dict:
    if not confirmed:
        raise LabSafetyError("Use --confirm-synthetic para criar paginacao no TEMP")
    lab = validate_lab(lab_dir)
    _, auditor_id = identities(lab.database)
    app = create_app(database_url=lab.database_url, api_key=LOCAL_KEY)

    with TestClient(app, raise_server_exceptions=False) as client:
        auditor = bearer(client, lab.credentials, "auditor.demo", auditor_id)

        # Nothing is seeded or mutated unless the browser's API accepts this
        # TEMP-only token from the explicit SQLite connection.
        attest_running_backend(auditor, auditor_id)
        scope = client.get("/v1/me/queues", headers=auditor)
        require(scope.status_code, 200, "escopo")
        allowed = {q["id"] for q in scope.json()}
        if "n1" not in allowed or "n2" in allowed:
            raise LabSafetyError("Permissoes de auditor nao correspondem a N1 sem N2")

        batch = uuid4().hex
        synthetic = {"X-POC-Key": LOCAL_KEY}
        focus_id = None
        for i in range(COUNT):
            unique = f"ui-pagination-{batch}-{i:02d}"
            created = client.post(
                "/v1/handoffs",
                headers={**synthetic, "Idempotency-Key": unique},
                json={
                    "operation_id": "demo",
                    "integration_id": "demo-bot",
                    "queue_id": "n1",
                    "requester_label": "Pessoa sintetica",
                    "subject": "QA paginacao verificada",
                    "external_conversation_id": unique,
                },
            )
            require(created.status_code, 201, "atendimento")
            if i == COUNT - 1:
                focus_id = created.json()["id"]

        if not focus_id:
            raise LabSafetyError("Sessao sintetica de paginacao nao foi criada")

        for i in range(COUNT):
            msg = client.post(
                f"/v1/handoffs/{focus_id}/messages",
                headers=synthetic,
                json={
                    "sender": "USER",
                    "content": f"QA PAGINACAO - MENSAGEM SINTETICA {i + 1:02d}",
                    "external_message_id": f"ui-{batch}-{i:02d}",
                },
            )
            require(msg.status_code, 201, "mensagem")

        # Explicitly synthetic QA events; linked through the application's
        # provenance writer, never by inferring historical queue ownership.
        factory, engine = make_session_factory(lab.database_url)
        try:
            provenance = ProvenanceRecorder(engine)
            if not provenance.enabled or not provenance.audit_enabled:
                raise LabSafetyError("Proveniencia 006b4 inativa no laboratorio")
            with factory.begin() as db:
                handoff = db.get(HandoffSession, focus_id)
                if handoff is None or handoff.queue_id != "n1":
                    raise LabSafetyError("Atendimento QA nao pertence a N1")
                for _ in range(COUNT):
                    row = SessionEvent(
                        session_id=focus_id,
                        event_type=MARKER,
                        actor="QA_SYNTHETIC",
                    )
                    db.add(row)
                    db.flush()
                    provenance.event_for_handoff(db, handoff, row)
        finally:
            engine.dispose()

        first_list = client.get(
            "/v1/history/verified-sessions",
            headers=auditor, params={"queue_id": "n1", "page": 1},
        )
        second_list = client.get(
            "/v1/history/verified-sessions",
            headers=auditor, params={"queue_id": "n1", "page": 2},
        )
        require(first_list.status_code, 200, "lista_p1")
        require(second_list.status_code, 200, "lista_p2")
        l1 = first_list.json()
        l2 = second_list.json()
        if (
            l1["next_page"] != 2 or not l2["tickets"]
            or focus_id not in {row["session_id"] for row in l1["tickets"]}
        ):
            raise LabSafetyError("Lista nao confirmou a segunda pagina sintetica")

        url = f"/v1/handoffs/{focus_id}/verified-history"
        detail1 = client.get(
            url, headers=auditor, params={"queue_id": "n1"},
        )
        detail_msg2 = client.get(
            url, headers=auditor, params={
                "queue_id": "n1", "message_page": 2, "event_page": 1,
            },
        )
        detail_event2 = client.get(
            url, headers=auditor, params={
                "queue_id": "n1", "message_page": 1, "event_page": 2,
            },
        )
        for stage, result in (
            ("detalhe_p1", detail1),
            ("mensagem_p2", detail_msg2),
            ("evento_p2", detail_event2),
        ):
            require(result.status_code, 200, stage)
        a, m, e = detail1.json(), detail_msg2.json(), detail_event2.json()
        if not (
            a["message_next_page"] == 2
            and a["event_next_page"] == 2
            and a["message_page"] == 1
            and a["event_page"] == 1
            and m["message_page"] == 2
            and m["event_page"] == 1
            and e["message_page"] == 1
            and e["event_page"] == 2
            and len(a["messages"]) == 25
            and len(m["messages"]) == 2
            and len(a["events"]) == 25
            and len(e["events"]) == 3
            and m["message_next_page"] is None
            and e["event_next_page"] is None
        ):
            raise LabSafetyError("Paginacao independente nao passou no backend TEMP")
        if {q["id"] for q in client.get(
            "/v1/me/queues", headers=auditor,
        ).json()} != allowed:
            raise LabSafetyError("Permissoes do auditor mudaram durante fixture")

    return {
        "result": "PASS",
        "scope": "TEMP_SYNTHETIC_006B4_ONLY",
        "live_api_attested": True,
        "synthetic_sessions_added": COUNT,
        "synthetic_messages_added": COUNT,
        "synthetic_qa_events_added": COUNT,
        "verified_session_page_2": "AVAILABLE",
        "verified_message_page_2": "AVAILABLE",
        "verified_event_page_2": "AVAILABLE",
        "independent_message_event_paging": "PASS",
        "auditor_scope_unchanged": True,
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True)
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        result = run(args.lab, args.confirm_synthetic)
    except (LabSafetyError, AttestationSafetyError) as exc:
        raise SystemExit("REPROVADO: " + str(exc)) from None
    except (SchemaSafetyError, OSError, sqlite3.Error, KeyError, ValueError, TypeError):
        raise SystemExit(
            "REPROVADO: erro de contrato ou laboratorio TEMP; verifique o ambiente"
        ) from None
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
