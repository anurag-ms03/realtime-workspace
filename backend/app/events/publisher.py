import json
import logging
from aio_pika import Message, DeliveryMode
from app.events.connection import rabbitmq_manager
from app.events.schemas import EventBase
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


async def publish_event(event: EventBase) -> None:
    """
    Publish any EventBase subclass to the task.events exchange.
    - Routing key is taken directly from event.event_type  (e.g. "task.created")
    - Message is persistent (survives broker restart)
    - Each publish gets its own channel (safe for concurrent coroutines)
    """
    channel = await rabbitmq_manager.get_channel()

    try:
        exchange = await channel.get_exchange(ex.TASK_EVENTS_EXCHANGE)

        body = event.model_dump_json().encode()

        message = Message(
            body=body,
            content_type="application/json",
            delivery_mode=DeliveryMode.PERSISTENT,   # survives broker restart
            message_id=event.event_id,               # for deduplication
            type=event.event_type,                   # visible in mgmt UI
        )

        await exchange.publish(message, routing_key=event.event_type)

        logger.info(
            f"Event published | type={event.event_type} "
            f"id={event.event_id} routing_key={event.event_type}"
        )

    finally:
        await channel.close()   # always release, even on error