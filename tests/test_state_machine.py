"""Unit tests for the structural lifecycle graph."""

import pytest

from handoff_hub.domain.state_machine import (
    ALLOWED_TRANSITIONS,
    TERMINAL_STATUSES,
    HandoffStatus,
    InvalidStateTransition,
    assert_transition,
)


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (HandoffStatus.REQUESTED, HandoffStatus.QUEUED),
        (HandoffStatus.QUEUED, HandoffStatus.OFFERED),
        (HandoffStatus.OFFERED, HandoffStatus.ACTIVE),
        (HandoffStatus.OFFERED, HandoffStatus.QUEUED),
        (HandoffStatus.ACTIVE, HandoffStatus.TRANSFER_PENDING),
        (HandoffStatus.TRANSFER_PENDING, HandoffStatus.QUEUED),
        (HandoffStatus.ACTIVE, HandoffStatus.WRAP_UP),
        (HandoffStatus.WRAP_UP, HandoffStatus.CLOSED),
        (HandoffStatus.QUEUED, HandoffStatus.CANCELLED),
    ],
)
def test_valid_transitions(source: HandoffStatus, target: HandoffStatus) -> None:
    assert_transition(source, target)


@pytest.mark.parametrize("source", list(TERMINAL_STATUSES))
def test_terminal_states_cannot_transition(source: HandoffStatus) -> None:
    for target in HandoffStatus:
        with pytest.raises(InvalidStateTransition):
            assert_transition(source, target)


def test_invalid_jump() -> None:
    with pytest.raises(InvalidStateTransition):
        assert_transition(HandoffStatus.REQUESTED, HandoffStatus.CLOSED)


def test_noop_is_invalid() -> None:
    with pytest.raises(InvalidStateTransition):
        assert_transition(HandoffStatus.ACTIVE, HandoffStatus.ACTIVE)


def test_all_states_have_explicit_graph_entry() -> None:
    assert set(ALLOWED_TRANSITIONS) == set(HandoffStatus)
