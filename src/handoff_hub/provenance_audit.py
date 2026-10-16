"""SPEC-006B-3.2: read-only, aggregate evidence report for legacy provenance.

No message content, identity, access token, or requester name is queried or logged.
There is deliberately NO automatic backfill: legacy records remain unclassified.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from handoff_hub.schema_admin import DEFAULT_DB, verify_database


def provenance_report(database: Path) -> dict:
    signature = verify_database(database)
    revision = signature["revision"]
    counts = signature["row_counts"]
    result = {
        "mode": "READ_ONLY",
        "revision": revision,
        "integrity": signature["integrity"],
        "table_count": signature["table_count"],
        "sessions": counts["handoff_sessions"],
        "transfers": counts["session_transfers"],
        "messages": counts["messages"],
        "events": counts["session_events"],
        "backfill_applied": False,
    }
    if revision not in ("006b2_queue_provenance", "006b3_history_access_audit"):
        result["status"] = "NOT_MIGRATED"
        result["provenance_available"] = False
        return result

    with closing(sqlite3.connect(
        database.resolve().as_uri() + "?mode=ro", uri=True, timeout=10
    )) as db:
        db.execute("BEGIN")
        def count(sql: str) -> int:
            return int(db.execute(sql).fetchone()[0])

        segments = {
            "total": count("SELECT count(*) FROM session_queue_segments"),
            "verified": count(
                "SELECT count(*) FROM session_queue_segments "
                "WHERE provenance_state='VERIFIED'"
            ),
            "open": count(
                "SELECT count(*) FROM session_queue_segments WHERE ended_at IS NULL"
            ),
            "closed": count(
                "SELECT count(*) FROM session_queue_segments WHERE ended_at IS NOT NULL"
            ),
        }
        message = {
            "verified": count(
                "SELECT count(*) FROM message_queue_provenance "
                "WHERE confidence='VERIFIED' AND segment_id IS NOT NULL"
            ),
            "undetermined": count(
                "SELECT count(*) FROM message_queue_provenance "
                "WHERE confidence!='VERIFIED' OR segment_id IS NULL"
            ),
            "uncovered": count(
                "SELECT count(*) FROM messages m WHERE NOT EXISTS "
                "(SELECT 1 FROM message_queue_provenance p WHERE p.message_id=m.id)"
            ),
        }
        event = {
            "verified": count(
                "SELECT count(*) FROM session_event_queue_provenance "
                "WHERE confidence='VERIFIED' AND segment_id IS NOT NULL"
            ),
            "undetermined": count(
                "SELECT count(*) FROM session_event_queue_provenance "
                "WHERE confidence!='VERIFIED' OR segment_id IS NULL"
            ),
            "uncovered": count(
                "SELECT count(*) FROM session_events e WHERE NOT EXISTS "
                "(SELECT 1 FROM session_event_queue_provenance p WHERE p.event_id=e.id)"
            ),
        }
        sessions_without_segments = count(
            "SELECT count(*) FROM handoff_sessions h WHERE NOT EXISTS "
            "(SELECT 1 FROM session_queue_segments s WHERE s.session_id=h.id)"
        )
        inconsistent_open = count(
            "SELECT count(*) FROM (SELECT session_id FROM session_queue_segments "
            "WHERE ended_at IS NULL GROUP BY session_id HAVING count(*)>1)"
        )
        db.rollback()
    if sum(message.values()) != result["messages"]:
        raise RuntimeError("Message coverage totals are inconsistent")
    if sum(event.values()) != result["events"]:
        raise RuntimeError("Event coverage totals are inconsistent")
    result.update({
        "status": "REPORT_READY",
        "provenance_available": True,
        "segments": segments,
        "message_coverage": message,
        "event_coverage": event,
        "sessions_without_segments": sessions_without_segments,
        "inconsistent_open_segments": inconsistent_open,
        "safe_for_history_authorization": False,
    })
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description="Aggregate read-only queue provenance audit")
    parser.add_argument("--database", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    try:
        print(json.dumps(provenance_report(args.database), indent=2, ensure_ascii=False))
        return 0
    except (OSError, sqlite3.Error, RuntimeError) as exc:
        parser.exit(2, f"[SPEC-006B-3.2] READ-ONLY AUDIT FAILED: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
