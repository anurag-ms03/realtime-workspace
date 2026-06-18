import logging
from app.events.consumers.base import BaseConsumer
from app.events import exchanges as ex

logger = logging.getLogger(__name__)

# In-memory counters — in production these would go to Redis
_counters: dict = {
    "task.created": 0,
    "task.completed": 0,
    "task.updated": 0,
}


class TaskAnalyticsConsumer(BaseConsumer):
    """
    Tracks task event counters per workspace.
    In production this would write to Redis or a metrics store.
    """
    queue_name = ex.QUEUE_TASK_ANALYTICS

    async def handle_event(self, event_type: str, body: dict) -> None:
        payload = body.get("payload", {})
        workspace_id = payload.get("workspace_id", "unknown")

        if event_type in _counters:
            _counters[event_type] += 1

        logger.info(
            f"[ANALYTICS] event_type={event_type} "
            f"workspace={workspace_id} "
            f"counters={_counters}"
        )