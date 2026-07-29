import logging
import redis
from app.events.consumers.base import BaseConsumer
from app.events import exchanges as ex
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

COUNTER_EVENT_TYPES = ("task.created", "task.updated", "task.completed")


def _counters_key(workspace_id: str) -> str:
    return f"analytics:{workspace_id}:counters"


class TaskAnalyticsConsumer(BaseConsumer):
    """
    Tracks task event counters per workspace, persisted in Redis so they
    survive consumer restarts. A separate Celery Beat job periodically
    rolls these up into timestamped snapshots for historical/dashboard use.
    """
    queue_name = ex.QUEUE_TASK_ANALYTICS

    async def handle_event(self, event_type: str, body: dict) -> None:
        payload = body.get("payload", {})
        workspace_id = payload.get("workspace_id", "unknown")

        if event_type in COUNTER_EVENT_TYPES:
            _redis.hincrby(_counters_key(workspace_id), event_type, 1)

        current_counts = _redis.hgetall(_counters_key(workspace_id))
        logger.info(
            f"[ANALYTICS] event_type={event_type} "
            f"workspace={workspace_id} "
            f"counters={current_counts}"
        )