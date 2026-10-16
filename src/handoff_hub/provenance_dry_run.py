"""SPEC-006B-3.3: evidence-based legacy history assessment, DRY RUN ONLY.

This module NEVER writes database rows, emits ticket/user IDs, or authorizes
history. A transfer/event chain yields REVIEW candidates, not VERIFIED facts.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from collections import Counter, defaultdict
from contextlib import closing
from datetime import UTC, datetime
from pathlib import Path

from handoff_hub.schema_admin import DEFAULT_DB, verify_database

SCHEMA_PROVENANCE = "006b2_queue_provenance"
DISPOSITIONS = (
    "review_candidate",
    "no_transfer_evidence",
    "missing_transfer_event_evidence",
    "invalid_timestamps",
    "inconsistent_queue_chain",
    "current_queue_mismatch",
    "already_has_provenance",
)
MESSAGE_DISPOSITIONS = (
    "review_candidate",
    "boundary_ambiguous",
    "invalid_timestamp",
    "not_assessed",
)


def _utc(raw: str | None) -> datetime | None:
    if not raw:
        return None
    try:
        value = datetime.fromisoformat(raw)
    except (TypeError, ValueError):
        return None
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _lineage(session, transfers, transfer_events, queue_operations):
    """Build conditional interval candidates; fail closed for any discrepancy."""
    if not transfers:
        return "no_transfer_evidence", ()
    first_time = _utc(session["created_at"])
    if first_time is None:
        return "invalid_timestamps", ()
    if len(transfers) != len(transfer_events):
        return "missing_transfer_event_evidence", ()

    initial_queue = transfers[0]["from_queue_id"]
    if queue_operations.get(initial_queue) != session["operation_id"]:
        return "inconsistent_queue_chain", ()
    current_queue = initial_queue
    last_time = first_time
    intervals = []

    for i, (transfer, event) in enumerate(zip(transfers, transfer_events, strict=True)):
        at = _utc(transfer["created_at"])
        event_at = _utc(event["created_at"])
        if at is None or at <= last_time or event_at is None or event_at < at:
            return "invalid_timestamps", ()
        if (event["actor"] != transfer["from_operator_id"]
                or (i + 1 < len(transfers)
                    and (next_at := _utc(transfers[i + 1]["created_at"])) is not None
                    and event_at >= next_at)):
            return "missing_transfer_event_evidence", ()
        source, destination = transfer["from_queue_id"], transfer["to_queue_id"]
        if (source != current_queue or source == destination
                or queue_operations.get(source) != session["operation_id"]
                or queue_operations.get(destination) != session["operation_id"]):
            return "inconsistent_queue_chain", ()
        intervals.append((last_time, at))
        last_time = at
        current_queue = destination

    if current_queue != session["queue_id"]:
        return "current_queue_mismatch", ()
    intervals.append((last_time, None))
    return "review_candidate", tuple(intervals)


def _assess_message(timestamp: str | None, intervals) -> str:
    at = _utc(timestamp)
    if at is None:
        return "invalid_timestamp"
    for start, end in intervals:
        if at == start or (end is not None and at == end):
            return "boundary_ambiguous"
        if at > start and (end is None or at < end):
            return "review_candidate"
    return "not_assessed"


def dry_run_report(database: Path) -> dict:
    """Assess only chain evidence, without reading message content or writing data."""
    state = verify_database(database)
    version = state["revision"]
    if version not in (None, "006b1_poc_baseline", SCHEMA_PROVENANCE):
        raise RuntimeError("Unknown revision for the legacy dry run")
    summary = {
        "mode": "DRY_RUN_READ_ONLY",
        "schema_revision": version,
        "integrity": state["integrity"],
        "table_count": state["table_count"],
        "sessions": state["row_counts"]["handoff_sessions"],
        "transfers": state["row_counts"]["session_transfers"],
        "messages": state["row_counts"]["messages"],
        "events": state["row_counts"]["session_events"],
        "backfill_applied": False,
        "rows_written": 0,
        "safe_for_history_authorization": False,
        "candidate_is_verified": False,
    }
    uri = database.resolve().as_uri() + "?mode=ro"
    with closing(sqlite3.connect(uri, uri=True, timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA query_only=ON")
        db.execute("BEGIN")
        queues = {
            row["id"]: row["operation_id"] for row in db.execute(
                "SELECT id, operation_id FROM queues"
            )
        }
        sessions = db.execute(
            "SELECT id, operation_id, queue_id, created_at "
            "FROM handoff_sessions ORDER BY id"
        ).fetchall()
        transfers = defaultdict(list)
        for row in db.execute(
            "SELECT session_id, from_queue_id, to_queue_id, "
            "from_operator_id, created_at "
            "FROM session_transfers ORDER BY session_id, created_at, id"
        ):
            transfers[row["session_id"]].append(row)
        transfer_events = defaultdict(list)
        for row in db.execute(
            "SELECT session_id, actor, created_at FROM session_events "
            "WHERE event_type='TRANSFERRED' ORDER BY session_id, created_at, id"
        ):
            transfer_events[row["session_id"]].append(row)
        messages = defaultdict(list)
        for row in db.execute(
            "SELECT session_id, created_at FROM messages ORDER BY session_id, created_at, id"
        ):
            messages[row["session_id"]].append(row["created_at"])

        existing = set()
        if version == SCHEMA_PROVENANCE:
            existing.update(row[0] for row in db.execute(
                "SELECT DISTINCT session_id FROM session_queue_segments"
            ))
            existing.update(row[0] for row in db.execute(
                "SELECT DISTINCT m.session_id FROM messages m "
                "JOIN message_queue_provenance p ON p.message_id=m.id"
            ))
            existing.update(row[0] for row in db.execute(
                "SELECT DISTINCT e.session_id FROM session_events e "
                "JOIN session_event_queue_provenance p ON p.event_id=e.id"
            ))

        classification = Counter()
        message_assessment = Counter()
        for session in sessions:
            session_id = session["id"]
            if session_id in existing:
                disposition, intervals = "already_has_provenance", ()
            else:
                disposition, intervals = _lineage(
                    session, transfers[session_id], transfer_events[session_id], queues
                )
            classification[disposition] += 1
            if disposition != "review_candidate":
                message_assessment["not_assessed"] += len(messages[session_id])
            else:
                for at in messages[session_id]:
                    message_assessment[_assess_message(at, intervals)] += 1
        db.rollback()

    if sum(classification.values()) != summary["sessions"]:
        raise RuntimeError("Session assessment totals do not match the database")
    if sum(message_assessment.values()) != summary["messages"]:
        raise RuntimeError("Message assessment totals do not match the database")

    summary.update({
        "status": "ANALYSIS_ONLY",
        "session_assessment": {k: classification[k] for k in DISPOSITIONS},
        "message_assessment": {
            k: message_assessment[k] for k in MESSAGE_DISPOSITIONS
        },
        "event_assessment": {
            "not_assessed": summary["events"],
            "assignment_attempted": 0,
        },
        "interpretation": (
            "Continuity and timestamp matches are REVIEW CANDIDATES only; "
            "they are not trusted queue provenance or read authorization."
        ),
    })
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Read-only history reconstruction dry-run; no data is migrated"
    )
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    try:
        print(json.dumps(dry_run_report(args.database), indent=2, ensure_ascii=False))
        return 0
    except (OSError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(2, f"[SPEC-006B-3.3] DRY RUN FAILED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
