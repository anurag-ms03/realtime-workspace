from celery import Celery
from celery.schedules import crontab
from app.core.config import settings

celery_app = Celery(
    "realtime_workspace",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.workers.email_tasks",
        "app.workers.cleanup_tasks",
        "app.workers.analytics_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
)

celery_app.conf.beat_schedule = {
    "purge-expired-soft-deleted-workspaces-daily": {
        "task": "purge_expired_soft_deleted_workspaces",
        "schedule": crontab(hour=3, minute=0),
    },
    "rollup-task-analytics-every-15-minutes": {
        "task": "rollup_task_analytics",
        "schedule": crontab(minute="*/15"),
    },
}