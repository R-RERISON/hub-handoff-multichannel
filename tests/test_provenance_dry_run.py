"""SPEC-006B-3.3: read-only legacy reconstruction does not invent permissions."""
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import insert

from handoff_hub.poc_db import (
    HandoffSession,
    Message,
    SessionEvent,
    SessionTransfer,
    make_session_factory,
)
from handoff_hub.provenance_dry_run import dry_run_report
from handoff_hub.provenance_schema import SESSION_QUEUE_SEGMENTS
from handoff_hub.schema_admin import create_new, verify_database
from handoff_hub.seed_demo_auth import provision

START = datetime(2026, 10, 16, 15, 0, tzinfo=UTC)
BOUNDARY = START + timedelta(minutes=10)
PRIVATE = "NAO_EXIBIR_TEXTO_DO_ATENDIMENTO"


def example_database(tmp_path, *, versioned=False, transferred=True,
                     include_transfer_event=True, source_queue="n1"):
    database = tmp_path / ("versioned.db" if versioned else "legacy.db")
    if versioned:
        create_new(database, confirmed=True)
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    provision(factory, tmp_path / "credentials.txt")
    with factory.begin() as db:
        ticket = HandoffSession(
            id="case-dry-run", operation_id="demo", integration_id="demo-bot",
            queue_id="n2" if transferred else "n1",
            idempotency_key="dry-run-case", external_conversation_id="dry-run-chat",
            requester_label="Não divulgar solicitante",
            subject=PRIVATE, status="QUEUED", created_at=START,
        )
        db.add(ticket)
        db.flush()
        db.add(SessionEvent(
            session_id=ticket.id, event_type="QUEUED",
            actor="demo-bot", created_at=START + timedelta(seconds=1),
        ))
        if transferred:
            db.add(SessionTransfer(
                session_id=ticket.id, from_queue_id=source_queue,
                to_queue_id="n2", from_operator_id="op-ana",
                reason=PRIVATE, created_at=BOUNDARY,
            ))
            if include_transfer_event:
                db.add(SessionEvent(
                    session_id=ticket.id, event_type="TRANSFERRED",
                    actor="op-ana", created_at=BOUNDARY + timedelta(milliseconds=1),
                ))
        for index, at in enumerate((
            START + timedelta(minutes=5),
            BOUNDARY,
            BOUNDARY + timedelta(minutes=5),
        ), 1):
            db.add(Message(
                id=f"message-{index}", session_id=ticket.id, sender="USER",
                content=PRIVATE, external_message_id=f"external-dry-run-{index}",
                created_at=at,
            ))
    engine.dispose()
    return database


def test_chain_is_review_candidate_not_verified_authorization(tmp_path):
    database = example_database(tmp_path)
    before = verify_database(database)
    report = dry_run_report(database)
    assert report["mode"] == "DRY_RUN_READ_ONLY"
    assert report["status"] == "ANALYSIS_ONLY"
    assert report["schema_revision"] is None
    assert report["session_assessment"]["review_candidate"] == 1
    assert report["message_assessment"]["review_candidate"] == 2
    assert report["message_assessment"]["boundary_ambiguous"] == 1
    assert report["safe_for_history_authorization"] is False
    assert report["candidate_is_verified"] is False
    assert report["rows_written"] == 0
    assert report["backfill_applied"] is False
    assert PRIVATE not in json.dumps(report, ensure_ascii=False)
    assert "case-dry-run" not in json.dumps(report)
    assert verify_database(database) == before
    assert dry_run_report(database) == report  # deterministic and read-only


def test_no_transfer_history_is_not_assigned_to_current_queue(tmp_path):
    database = example_database(tmp_path, transferred=False)
    report = dry_run_report(database)
    assert report["session_assessment"]["no_transfer_evidence"] == 1
    assert report["session_assessment"]["review_candidate"] == 0
    assert report["message_assessment"]["not_assessed"] == 3
    assert report["safe_for_history_authorization"] is False


def test_missing_transfer_event_rejects_candidate(tmp_path):
    database = example_database(tmp_path, include_transfer_event=False)
    report = dry_run_report(database)
    assert report["session_assessment"]["missing_transfer_event_evidence"] == 1
    assert report["message_assessment"]["not_assessed"] == 3


def test_inconsistent_transfer_source_rejects_candidate(tmp_path):
    database = example_database(tmp_path, source_queue="n2")
    report = dry_run_report(database)
    assert report["session_assessment"]["inconsistent_queue_chain"] == 1
    assert report["session_assessment"]["review_candidate"] == 0
    assert report["message_assessment"]["not_assessed"] == 3


def test_existing_provenance_is_never_reassessed_for_backfill(tmp_path):
    database = example_database(tmp_path, versioned=True)
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    with factory.begin() as db:
        db.execute(insert(SESSION_QUEUE_SEGMENTS).values(
            id="segment-dry-run", session_id="case-dry-run",
            queue_id="n2", ordinal=0, started_at=BOUNDARY,
            ended_at=None, transfer_id=None,
            provenance_state="VERIFIED",
        ))
    engine.dispose()
    before = verify_database(database)
    report = dry_run_report(database)
    assert report["schema_revision"] == "006b2_queue_provenance"
    assert report["session_assessment"]["already_has_provenance"] == 1
    assert report["session_assessment"]["review_candidate"] == 0
    assert report["message_assessment"]["not_assessed"] == 3
    assert verify_database(database) == before


def test_chain_analyzer_does_not_accept_message_timestamps_before_intake(tmp_path):
    database = example_database(tmp_path)
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    with factory.begin() as db:
        msg = db.get(Message, "message-1")
        msg.created_at = START - timedelta(seconds=1)
    engine.dispose()
    report = dry_run_report(database)
    assert report["session_assessment"]["review_candidate"] == 1
    assert report["message_assessment"]["review_candidate"] == 1
    assert report["message_assessment"]["boundary_ambiguous"] == 1
    assert report["message_assessment"]["not_assessed"] == 1


def test_transfer_event_actor_mismatch_is_not_trusted(tmp_path):
    database = example_database(tmp_path)
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    with factory.begin() as db:
        event = next(
            row for row in db.query(SessionEvent).all()
            if row.event_type == "TRANSFERRED"
        )
        event.actor = "op-bruno"
    engine.dispose()
    report = dry_run_report(database)
    assert report["session_assessment"]["missing_transfer_event_evidence"] == 1
    assert report["message_assessment"]["not_assessed"] == 3


def test_current_queue_disagreement_blocks_historical_candidate(tmp_path):
    database = example_database(tmp_path)
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    with factory.begin() as db:
        db.get(HandoffSession, "case-dry-run").queue_id = "n1"
    engine.dispose()
    report = dry_run_report(database)
    assert report["session_assessment"]["current_queue_mismatch"] == 1
    assert report["message_assessment"]["review_candidate"] == 0


def test_transfer_before_session_creation_is_blocked(tmp_path):
    database = example_database(tmp_path)
    factory, engine = make_session_factory(f"sqlite:///{database.as_posix()}")
    with factory.begin() as db:
        transfer = db.query(SessionTransfer).one()
        transfer.created_at = START - timedelta(minutes=1)
    engine.dispose()
    report = dry_run_report(database)
    assert report["session_assessment"]["invalid_timestamps"] == 1
    assert report["message_assessment"]["not_assessed"] == 3
