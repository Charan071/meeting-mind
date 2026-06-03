from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "meetingmind",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "app.workers.tasks.process_meeting_transcript": {"queue": "extraction"},
        "app.workers.tasks.send_overdue_nudges": {"queue": "notifications"},
    },
    beat_schedule={
        "weekly-overdue-nudges": {
            "task": "app.workers.tasks.send_overdue_nudges",
            "schedule": crontab(hour=9, minute=0, day_of_week="monday"),
        },
        # Safety-net: check every 5 min for scheduled meetings that should join now
        # (covers cases where the calendar webhook was missed or the eta job was lost)
        "check-upcoming-meetings": {
            "task": "app.workers.tasks.check_and_join_upcoming",
            "schedule": crontab(minute="*/5"),
        },
    },
)
