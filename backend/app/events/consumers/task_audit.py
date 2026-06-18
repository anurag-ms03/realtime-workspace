import logging
from app.events.consumers.base import BaseConsumer
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


class TaskAuditConsumer(BaseConsumer):
    """
    Writes a structured audit trail for every task event.
    In production this would persist to a dedicated audit store
    or stream to something like Elasticsearch.
    """
    queue_name = ex.QUEUE_TASK_AUDIT

    async def handle_event(self, event_type: str, body: dict) -> None:
        payload = body.get("payload", {})
        event_id = body.get("event_id")
        occurred_at = body.get("occurred_at")

        logger.info(
            f"[AUDIT] event_type={event_type} "
            f"event_id={event_id} "
            f"task_id={payload.get('task_id')} "
            f"project_id={payload.get('project_id')} "
            f"workspace_id={payload.get('workspace_id')} "
            f"occurred_at={occurred_at} "
            f"changes={payload.get('changes', {})}"
        )