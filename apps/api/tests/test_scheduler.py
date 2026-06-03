"""Tests for meeting bot scheduler."""
import pytest
from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch


def test_schedule_bot_join_future():
    future = datetime.now(UTC) + timedelta(hours=1)
    mock_result = MagicMock()
    mock_result.id = "task-abc"

    with patch("app.services.scheduler.auto_join_meeting") as mock_task:
        mock_task.apply_async.return_value = mock_result
        from app.services.scheduler import schedule_bot_join
        task_id = schedule_bot_join("meet-1", future)

    assert task_id == "task-abc"
    mock_task.apply_async.assert_called_once()
    call_kwargs = mock_task.apply_async.call_args.kwargs
    assert call_kwargs["args"] == ["meet-1"]
    # eta should be ~60 seconds before start
    expected_eta = future - timedelta(seconds=60)
    assert abs((call_kwargs["eta"] - expected_eta).total_seconds()) < 2


def test_schedule_bot_join_past_fires_immediately():
    past = datetime.now(UTC) - timedelta(minutes=10)
    mock_result = MagicMock()
    mock_result.id = "task-now"

    with patch("app.services.scheduler.auto_join_meeting") as mock_task:
        mock_task.apply_async.return_value = mock_result
        from app.services.scheduler import schedule_bot_join
        task_id = schedule_bot_join("meet-2", past)

    assert task_id == "task-now"
    call_kwargs = mock_task.apply_async.call_args.kwargs
    # eta should be ~now (within 10 seconds)
    assert (datetime.now(UTC) - call_kwargs["eta"]).total_seconds() < 10


def test_cancel_scheduled_join():
    with patch("app.services.scheduler.celery_app") as mock_app:
        from app.services.scheduler import cancel_scheduled_join
        cancel_scheduled_join("task-xyz")
        mock_app.control.revoke.assert_called_once_with("task-xyz", terminate=False)
