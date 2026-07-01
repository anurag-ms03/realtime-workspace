import logging
from app.events.connection import rabbitmq_manager
from app.events.consumers.task_notifications import TaskNotificationsConsumer
from app.events.consumers.task_audit import TaskAuditConsumer
from app.events.consumers.task_analytics import TaskAnalyticsConsumer
from app.events.consumers.dlq_inspector import DLQInspector
from app.events import exchanges as ex

logger = logging.getLogger(__name__)

# All registered consumers
_consumers = [
    TaskNotificationsConsumer(),
    TaskAuditConsumer(),
    TaskAnalyticsConsumer(),
]

_dlq_inspectors = [
    DLQInspector(ex.DLQ_TASK_NOTIFICATIONS, ex.QUEUE_TASK_NOTIFICATIONS),
    DLQInspector(ex.DLQ_TASK_AUDIT, ex.QUEUE_TASK_AUDIT),
    DLQInspector(ex.DLQ_TASK_ANALYTICS, ex.QUEUE_TASK_ANALYTICS),
]

   
async def start_consumers() -> None:
    """
    Start all consumers. Each gets its own channel.
    Called once at app startup after topology is declared.
    """
    
    for consumer in _consumers:
        channel = await rabbitmq_manager.get_channel()
        await consumer.start(channel)

    for inspector in _dlq_inspectors:
        channel = await rabbitmq_manager.get_channel()
        await inspector.start(channel)

    logger.info(
        f"All {len(_consumers)} consumers + "
        f"{len(_dlq_inspectors)} DLQ inspectors started ✓"
    )
    
async def stop_consumers() -> None:
    logger.info("Consumers stopped.")
    