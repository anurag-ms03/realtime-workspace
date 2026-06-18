import logging
from app.events.connection import rabbitmq_manager
from app.events.consumers.task_notifications import TaskNotificationsConsumer
from app.events.consumers.task_audit import TaskAuditConsumer
from app.events.consumers.task_analytics import TaskAnalyticsConsumer

logger = logging.getLogger(__name__)

# All registered consumers
_consumers = [
    TaskNotificationsConsumer(),
    TaskAuditConsumer(),
    TaskAnalyticsConsumer(),
]


async def start_consumers() -> None:
    """
    Start all consumers. Each gets its own channel.
    Called once at app startup after topology is declared.
    """
    for consumer in _consumers:
        channel = await rabbitmq_manager.get_channel()
        await consumer.start(channel)

    logger.info(f"All {len(_consumers)} consumers started ✓")


async def stop_consumers() -> None:
    """Placeholder — aio_pika cleans up channels on connection close."""
    logger.info("Consumers stopped.")