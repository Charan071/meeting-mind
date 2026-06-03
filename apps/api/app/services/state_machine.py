"""Action item state machine.

Valid transitions:
  open        → in_progress, done, overdue, deferred
  in_progress → done, overdue, deferred
  overdue     → done, in_progress, deferred
  deferred    → open, done
  done        → (terminal — no transitions)
"""
from __future__ import annotations

VALID_TRANSITIONS: dict[str, set[str]] = {
    "open":        {"in_progress", "done", "overdue", "deferred"},
    "in_progress": {"done", "overdue", "deferred"},
    "overdue":     {"done", "in_progress", "deferred"},
    "deferred":    {"open", "done"},
    "done":        set(),
}


class InvalidTransitionError(ValueError):
    pass


def validate_transition(current: str, target: str) -> None:
    allowed = VALID_TRANSITIONS.get(current, set())
    if target not in allowed:
        raise InvalidTransitionError(
            f"Cannot transition action item from '{current}' to '{target}'. "
            f"Allowed: {sorted(allowed) or 'none (terminal state)'}."
        )


def can_transition(current: str, target: str) -> bool:
    return target in VALID_TRANSITIONS.get(current, set())
