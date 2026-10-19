"""SPEC-006C: disposable, attested UX-02/UX-05 N1 to N2 browser fixture.

Only an explicitly validated TEMP/006b4 lab may be mutated. A live server
is consulted only via an authenticated GET before any synthetic write.
Never prints conversation IDs, credentials, tokens, or message bodies.
Backend PASS never substitutes manual UX/viewport acceptance.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path
from uuid import uuid4

from fastapi.testclient import TestClient

from handoff_hub.poc_api import create_app
from handoff_hub.poc_db import HandoffSession, make_session_factory
from handoff_hub.schema_admin import SchemaSafetyError
from scripts.lab_environment import LabSafetyError, validate_lab
from scripts.release_grant_toggle import (
    LabSafetyError as AttestationSafetyError,
    attest_running_backend,
    bearer,
)

QA_KEY = "spec006c-testclient-only"
N1_TEXT = "QA 006C mensagem sintetica da fila N1"
N2_TEXT = "QA 006C mensagem sintetica da fila N2"
PRIVATE_NOTE = "QA 006C nota privada somente operadores"


def require(response, status: int, step: str) -> None:
    if response.status_code != status:
        raise LabSafetyError(
            f"QA {step}: HTTP {response.status_code}, esperado {status}"
        )


def accounts_and_grants(database: Path) -> tuple[str, str]:
    with closing(sqlite3.connect(
        database.as_uri() + "?mode=ro", uri=True, timeout=10,
    )) as db:
        db.execute("PRAGMA query_only=ON")
        users = dict(db.execute(
            "SELECT username, id FROM auth_users WHERE "
            "username IN ('auditor.demo', 'supervisor.demo')"
        ).fetchall())
        if set(users) != {"auditor.demo", "supervisor.demo"}:
            raise LabSafetyError("Contas sinteticas de QA ausentes")
        # The operator-facing UX-05 scenario requires a clean N2 queue and
        # an available seat. Refuse before any synthetic session is created,
        # rather than consuming another case's offer or partially seeding QA.
        operator = db.execute(
            "SELECT presence, capacity FROM operators WHERE id='op-bruno'"
        ).fetchone()
        membership = db.execute(
            "SELECT count(*) FROM queue_memberships "
            "WHERE queue_id='n2' AND operator_id='op-bruno'"
        ).fetchone()[0]
        existing = db.execute(
            "SELECT count(*) FROM handoff_sessions "
            "WHERE (queue_id='n2' AND status='QUEUED') "
            "OR (operator_id='op-bruno' AND status IN ('ACTIVE','OFFERED'))"
        ).fetchone()[0]
        if (
            operator is None or operator[0] != "AVAILABLE"
            or operator[1] < 1 or membership != 1 or existing
        ):
            raise LabSafetyError("Fila/operador N2 nao estao livres no TEMP")
        for username, role, expected in (
            ("auditor.demo", "AUDITOR", {"n1"}),
            ("supervisor.demo", "SUPERVISOR", {"n1", "n2"}),
        ):
            got = {row[0] for row in db.execute(
                "SELECT queue_id FROM queue_role_grants "
                "WHERE user_id=? AND role=?",
                (users[username], role),
            )}
            if got != expected:
                raise LabSafetyError(f"Grants sinteticos invalidos para {role}")
        return users["auditor.demo"], users["supervisor.demo"]


def run(lab_dir: str | Path, confirmed: bool) -> dict:
    if not confirmed:
        raise LabSafetyError("Use --confirm-synthetic antes de qualquer escrita")
    lab = validate_lab(lab_dir)
    auditor_id, supervisor_id = accounts_and_grants(lab.database)
    app = create_app(database_url=lab.database_url, api_key=QA_KEY)

    with TestClient(app, raise_server_exceptions=False) as client:
        auditor = bearer(client, lab.credentials, "auditor.demo", auditor_id)
        supervisor = bearer(client, lab.credentials, "supervisor.demo", supervisor_id)

        # Fail before mutation if browser API does not recognize the TEMP token.
        attest_running_backend(auditor, auditor_id)
        for principal, expected, title in (
            (auditor, {"n1"}, "AUDITOR"),
            (supervisor, {"n1", "n2"}, "SUPERVISOR"),
        ):
            scope = client.get("/v1/me/queues", headers=principal)
            require(scope, 200, title + "_scope")
            if {q["id"] for q in scope.json()} != expected:
                raise LabSafetyError("Escopo inesperado no endpoint " + title)

        nonce = uuid4().hex
        local = {"X-POC-Key": QA_KEY}
        created = client.post(
            "/v1/handoffs",
            headers={**local, "Idempotency-Key": "qa-ux02-05-" + nonce},
            json={
                "operation_id": "demo", "integration_id": "demo-bot",
                "queue_id": "n1", "requester_label": "Pessoa sintetica QA",
                "subject": "QA 006C transferencia N1 N2",
                "external_conversation_id": "qa-ux02-05-" + nonce,
            },
        )
        require(created, 201, "create_session")
        session_id = created.json()["id"]

        first = client.post(
            f"/v1/handoffs/{session_id}/messages",
            headers=local,
            json={"sender": "USER", "content": N1_TEXT,
                  "external_message_id": "qa-n1-" + nonce},
        )
        require(first, 201, "create_n1_message")

        # Set only the synthetic ACTIVE/owner test precondition.
        # The transfer itself is executed by the real API.
        factory, engine = make_session_factory(lab.database_url)
        try:
            with factory.begin() as db:
                ticket = db.get(HandoffSession, session_id)
                if ticket is None or ticket.queue_id != "n1":
                    raise LabSafetyError("Atendimento QA nao pertence a N1")
                ticket.status = "ACTIVE"
                ticket.operator_id = "op-ana"
        finally:
            engine.dispose()

        transfer = client.post(
            f"/v1/handoffs/{session_id}/transfer",
            headers=local,
            json={"operator_id": "op-ana", "queue_id": "n2",
                  "reason": PRIVATE_NOTE},
        )
        require(transfer, 200, "transfer_n1_n2")
        if transfer.json().get("status") != "QUEUED" or transfer.json().get("queue_id") != "n2":
            raise LabSafetyError("Transferencia sintetica nao confirmada")

        second = client.post(
            f"/v1/handoffs/{session_id}/messages",
            headers=local,
            json={"sender": "USER", "content": N2_TEXT,
                  "external_message_id": "qa-n2-" + nonce},
        )
        require(second, 201, "create_n2_message")

        for queue, principal, expected in (
            ("n1", auditor, N1_TEXT),
            ("n1", supervisor, N1_TEXT),
            ("n2", supervisor, N2_TEXT),
        ):
            detail = client.get(
                f"/v1/handoffs/{session_id}/verified-history",
                params={"queue_id": queue}, headers=principal,
            )
            require(detail, 200, "verified_" + queue)
            data = detail.json()
            if (
                data.get("scope") != "RUNTIME_VERIFIED_QUEUE_ONLY"
                or data.get("partial_history") is not True
                or [m["content"] for m in data["messages"]] != [expected]
                or PRIVATE_NOTE in detail.text
            ):
                raise LabSafetyError("Historico de fila vazou conteudo ou nota privada")

        denied = client.get(
            f"/v1/handoffs/{session_id}/verified-history",
            params={"queue_id": "n2"}, headers=auditor,
        )
        require(denied, 404, "auditor_cross_queue")
        if any(secret in denied.text for secret in (
            session_id, N1_TEXT, N2_TEXT, PRIVATE_NOTE
        )):
            raise LabSafetyError("Negativa de fila revelou conteudo protegido")

        forbidden = client.post(
            f"/v1/handoffs/{session_id}/messages",
            headers=supervisor,
            json={"sender": "OPERATOR", "operator_id": "op-bruno",
                  "content": "Mensagem proibida QA",
                  "external_message_id": "qa-forbidden-" + nonce},
        )
        require(forbidden, 403, "supervisor_cannot_send_as_operator")

        for queue in ("n1", "n2"):
            listing = client.get(
                "/v1/history/verified-sessions",
                params={"queue_id": queue}, headers=supervisor,
            )
            require(listing, 200, "supervisor_list_" + queue)
            if session_id not in {t["session_id"] for t in listing.json()["tickets"]}:
                raise LabSafetyError("Sessao QA nao aparece na fila concedida")

        # Complete the N2 operator screen scenario using real dispatch/accept
        # endpoints. A queue in use by another QA scenario is not silently
        # altered: fail if this fixture did not receive its own session.
        offer = client.post(
            "/v1/dispatch/offer", headers=local, json={"queue_id": "n2"},
        )
        require(offer, 200, "offer_n2")
        offering = offer.json()
        if (
            offering.get("result") != "offered"
            or offering.get("offer", {}).get("session_id") != session_id
            or offering["offer"].get("operator_id") != "op-bruno"
        ):
            raise LabSafetyError("Oferta N2 nao corresponde ao atendimento sintetico")
        accepted = client.post(
            f"/v1/handoffs/{session_id}/accept",
            headers=local, json={"operator_id": "op-bruno"},
        )
        require(accepted, 200, "accept_n2")
        if accepted.json().get("status") != "ACTIVE":
            raise LabSafetyError("Sessao N2 nao ficou ativa para Bruno")
        work = client.get("/v1/operators/op-bruno/work", headers=local)
        require(work, 200, "operator_n2_work")
        if session_id not in {item["id"] for item in work.json()["active"]}:
            raise LabSafetyError("Mesa N2 nao apresenta atendimento ativo QA")
        timeline = client.get(
            f"/v1/handoffs/{session_id}/timeline", headers=local,
        )
        require(timeline, 200, "operator_private_timeline")
        if not any(
            entry.get("reason") == PRIVATE_NOTE
            for entry in timeline.json().get("transfers", [])
        ):
            raise LabSafetyError("Nota privada ausente na trilha do operador")
        transcript = client.get(
            f"/v1/handoffs/{session_id}/messages", headers=local,
        )
        require(transcript, 200, "customer_transcript")
        if PRIVATE_NOTE in transcript.text:
            raise LabSafetyError("Nota privada vazou para mensagens ao cliente")

    return {
        "result": "PASS",
        "scope": "TEMP_SYNTHETIC_006B4_ONLY",
        "ux02_backend_scope": "PASS",
        "ux05_backend_verified_isolation": "PASS",
        "ux05_n2_operator_ready": "PASS",
        "supervisor_queue_count": 2,
        "auditor_n2_http": 404,
        "supervisor_operator_write_http": 403,
        "private_note_exposed": False,
        "synthetic_sessions_added": 1,
        "synthetic_messages_added": 2,
        "live_api_attested_before_writes": True,
        "manual_ux02": "NOT_RUN",
        "manual_ux05": "NOT_RUN",
        "manual_ux08": "BLOCKED",
        "original_database_touched": False,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--lab", required=True)
    parser.add_argument("--confirm-synthetic", action="store_true")
    args = parser.parse_args()
    try:
        outcome = run(args.lab, args.confirm_synthetic)
    except (LabSafetyError, AttestationSafetyError) as exc:
        raise SystemExit("REPROVADO: " + str(exc)) from None
    except (SchemaSafetyError, OSError, sqlite3.Error, ValueError, KeyError, TypeError):
        raise SystemExit("REPROVADO: laboratorio ou contrato QA indisponivel") from None
    print(json.dumps(outcome, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
