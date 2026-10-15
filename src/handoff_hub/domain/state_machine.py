"""Pure provisional lifecycle validation, not a production workflow engine.

Authorization, reservation and transactional concurrency guards belong to
SPEC-002; validating the graph alone is never sufficient to mutate a session.
"""

from enum import StrEnum


class HandoffStatus(StrEnum):
    REQUESTED = "REQUESTED"
    QUEUED = "QUEUED"
    OFFERED = "OFFERED"
    ACTIVE = "ACTIVE"
    TRANSFER_PENDING = "TRANSFER_PENDING"
    WRAP_UP = "WRAP_UP"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"
    ABANDONED = "ABANDONED"
    EXPIRED = "EXPIRED"


TERMINAL_STATUSES: frozenset[HandoffStatus] = frozenset(
    {
        HandoffStatus.CLOSED,
        HandoffStatus.CANCELLED,
        HandoffStatus.ABANDONED,
        HandoffStatus.EXPIRED,
    }
)

ALLOWED_TRANSITIONS: dict[HandoffStatus, frozenset[HandoffStatus]] = {
    HandoffStatus.REQUESTED: frozenset(
        {HandoffStatus.QUEUED, HandoffStatus.CANCELLED, HandoffStatus.EXPIRED}
    ),
    HandoffStatus.QUEUED: frozenset(
        {HandoffStatus.OFFERED, HandoffStatus.CANCELLED, HandoffStatus.EXPIRED}
    ),
    HandoffStatus.OFFERED: frozenset(
        {
            HandoffStatus.ACTIVE,
            HandoffStatus.QUEUED,
            HandoffStatus.CANCELLED,
            HandoffStatus.EXPIRED,
        }
    ),
    HandoffStatus.ACTIVE: frozenset(
        {HandoffStatus.WRAP_UP, HandoffStatus.TRANSFER_PENDING, HandoffStatus.ABANDONED}
    ),
    HandoffStatus.TRANSFER_PENDING: frozenset(
        {HandoffStatus.QUEUED, HandoffStatus.ACTIVE, HandoffStatus.ABANDONED}
    ),
    HandoffStatus.WRAP_UP: frozenset({HandoffStatus.CLOSED}),
    HandoffStatus.CLOSED: frozenset(),
    HandoffStatus.CANCELLED: frozenset(),
    HandoffStatus.ABANDONED: frozenset(),
    HandoffStatus.EXPIRED: frozenset(),
}


class InvalidStateTransition(ValueError):
    """A requested transition is disallowed by the lifecycle graph."""


def assert_transition(current: HandoffStatus, target: HandoffStatus) -> None:
    """Reject disallowed transitions, including no-op transitions."""
    if target not in ALLOWED_TRANSITIONS[current]:
        raise InvalidStateTransition(f"Invalid handoff transition: {current} -> {target}")
