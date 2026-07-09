import logging
from uuid import UUID
from app.events.consumers.base import BaseConsumer
from app.events import exchanges as ex
from app.ws.manager import manager

logger = logging.getLogger(__name__)


class TaskNotificationsConsumer(BaseConsumer):
    """
    Handles task.created, task.updated, and task.completed events.
    In production this would send emails / push notifications.
    Also bridges these events out to connected WebSocket clients in
    the relevant workspace for realtime updates.
    """
    queue_name = ex.QUEUE_TASK_NOTIFICATIONS

    async def handle_event(self, event_type: str, body: dict) -> None:
        payload = body.get("payload", {})

        if payload.get("title") == "FAIL_TEST":
            raise RuntimeError("Simulated failure for DLQ testing")

        workspace_id = payload.get("workspace_id")

        if event_type == "task.created":
            logger.info(
                f"[NOTIFICATION] New task created → "
                f"title='{payload.get('title')}' "
                f"workspace={workspace_id} "
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
            logger.info(
                f"[NOTIFICATION] Task updated → "
                f"task_id={payload.get('task_id')} "
                f"updated_by={payload.get('updated_by')} "
                f"changes={payload.get('changes')}"
            )

        else:
            logger.warning(f"[NOTIFICATION] Unknown event type: {event_type}")
            return

        # ── Realtime broadcast ──────────────────────────────────────────
        if workspace_id:
            await manager.broadcast_to_workspace(
                UUID(workspace_id),
                {"type": event_type, "payload": payload},
            )