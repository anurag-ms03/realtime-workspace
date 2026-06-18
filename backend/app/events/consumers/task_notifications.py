import logging
from app.events.consumers.base import BaseConsumer
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


class TaskNotificationsConsumer(BaseConsumer):
    """
    Handles task.created and task.completed events.
    In production this would send emails / push notifications.
    For now logs the intent clearly so we can verify the pipeline.
    """
    queue_name = ex.QUEUE_TASK_NOTIFICATIONS

    async def handle_event(self, event_type: str, body: dict) -> None:
        payload = body.get("payload", {})

        if event_type == "task.created":
            logger.info(
                f"[NOTIFICATION] New task created → "
                f"title='{payload.get('title')}' "
                f"workspace={payload.get('workspace_id')} "
                f"assignee={payload.get('assignee_id') or 'unassigned'}"
            )

        elif event_type == "task.completed":
            logger.info(
                f"[NOTIFICATION] Task completed → "
                f"title='{payload.get('title')}' "
                f"completed_by={payload.get('completed_by')} "
                f"at={payload.get('completed_at')}"
            )

        elif event_type == "task.updated":
            # Notifications consumer ignores plain updates
            pass

        else:
            logger.warning(f"[NOTIFICATION] Unknown event type: {event_type}")