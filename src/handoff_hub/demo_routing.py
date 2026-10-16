"""Idempotent demo-only routing baseline, separate from production queue policies.

N1: Ana. N2: Bruno. Future intentional supervisor changes are preserved by
storing the applied seed revision. Never rewrite existing active assignments.
"""

from sqlalchemy import select
from sqlalchemy.orm import Session

from handoff_hub.poc_db import (
    DemoSeedRevision,
    HandoffOffer,
    HandoffSession,
    QueueMembership,
    SessionEvent,
    utc_now,
)

DEMO_ROUTING_REVISION = "demo_n1_ana_n2_bruno_v1"
DEFAULT_INTAKE_QUEUE_ID = "n1"


def configure_demo_routing(db: Session) -> bool:
    """One-time baseline correction, safe for populated SQLite POC databases.

    Requires demo queues and operators to have been flushed first.
    An offered N1 session reserved to Bruno is requeued; an ACTIVE session
    stays with Bruno so no ongoing conversation is interrupted.
    """
    if db.get(DemoSeedRevision, DEMO_ROUTING_REVISION) is not None:
        return False

    for queue_id, operator_id in (("n1", "op-ana"), ("n2", "op-bruno")):
        if db.get(QueueMembership, (queue_id, operator_id)) is None:
            db.add(QueueMembership(queue_id=queue_id, operator_id=operator_id))

    old_membership = db.get(QueueMembership, ("n1", "op-bruno"))
    if old_membership is not None:
        offered = db.scalars(
            select(HandoffSession).where(
                HandoffSession.queue_id == "n1",
                HandoffSession.operator_id == "op-bruno",
                HandoffSession.status == "OFFERED",
            )
        ).all()
        for handoff in offered:
            offers = db.scalars(
                select(HandoffOffer).where(
                    HandoffOffer.session_id == handoff.id,
                    HandoffOffer.operator_id == "op-bruno",
                    HandoffOffer.status == "PENDING",
                )
            ).all()
            for offer in offers:
                offer.status = "EXPIRED"
                offer.resolved_at = utc_now()
            handoff.status = "QUEUED"
            handoff.operator_id = None
            handoff.updated_at = utc_now()
            db.add(
                SessionEvent(
                    session_id=handoff.id,
                    event_type="DEMO_ROUTING_POLICY_UPDATED",
                    actor="demo-seed",
                )
            )
        db.delete(old_membership)

    db.add(DemoSeedRevision(id=DEMO_ROUTING_REVISION))
    db.flush()
    return True
