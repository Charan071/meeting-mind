"""State machine transition validation tests."""
import pytest
from app.services.state_machine import (
    InvalidTransitionError,
    can_transition,
    validate_transition,
)


def test_open_to_in_progress():
    validate_transition("open", "in_progress")  # should not raise


def test_open_to_done():
    validate_transition("open", "done")


def test_done_is_terminal():
    with pytest.raises(InvalidTransitionError):
        validate_transition("done", "open")


def test_done_to_in_progress_invalid():
    with pytest.raises(InvalidTransitionError):
        validate_transition("done", "in_progress")


def test_overdue_to_done():
    validate_transition("overdue", "done")


def test_overdue_to_in_progress():
    validate_transition("overdue", "in_progress")


def test_deferred_to_open():
    validate_transition("deferred", "open")


def test_can_transition_false():
    assert can_transition("done", "open") is False
    assert can_transition("done", "in_progress") is False


def test_can_transition_true():
    assert can_transition("open", "done") is True
    assert can_transition("overdue", "deferred") is True


def test_unknown_state_no_crash():
    # Unknown current state → no allowed transitions → should raise
    with pytest.raises(InvalidTransitionError):
        validate_transition("unknown_state", "open")
