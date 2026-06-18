import json
import logging
from abc import ABC, abstractmethod
from typing import Optional
import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from app.events.schemas import EventBase

logger = logging.getLogger(__name__)


class BaseConsumer(ABC):
    """
    Base class for all event consumers.
    Handles ack/nack, retry counting, and DLQ routing automatically.
    Subclasses just implement handle_event().
    """

    MAX_RETRIES = 3
    queue_name: str = ""

    def __init__(self):
        self._channel = None
        self._queue = None

    async def start(self, channel: aio_pika.Channel) -> None:
        self._channel = channel
        self._queue = await channel.get_queue(self.queue_name)
        await self._queue.consume(self._on_message)
        logger.info(f"Consumer started → listening on queue: {self.queue_name}")

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        retry_count = int(message.headers.get("x-retry-count", 0))

        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type", "unknown")
            event_id = body.get("event_id", "unknown")

            logger.info(
                f"[{self.queue_name}] Received event | "
                f"type={event_type} id={event_id} retry={retry_count}"
            )

            await self.handle_event(event_type, body)
            await message.ack()

            logger.info(
                f"[{self.queue_name}] ACK | type={event_type} id={event_id}"
            )

        except Exception as e:
            logger.error(
                f"[{self.queue_name}] Error processing message | "
                f"retry={retry_count} error={e}"
            )
            await self._handle_failure(message, retry_count, e)

    async def _handle_failure(
        self,
        message: AbstractIncomingMessage,
        retry_count: int,
        error: Exception,
    ) -> None:
        if retry_count < self.MAX_RETRIES:
            # Requeue with incremented retry count
            await self._channel.default_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers={
                        **dict(message.headers),
                        "x-retry-count": retry_count + 1,
                        "x-last-error": str(error),
                    },
                ),
                routing_key=self.queue_name,
            )
            await message.ack()  # ack original, we republished with new headers
            logger.warning(
                f"[{self.queue_name}] Requeued for retry "
                f"{retry_count + 1}/{self.MAX_RETRIES}"
            )
        else:
            # Max retries exceeded → let DLX handle it via nack
            await message.nack(requeue=False)
            logger.error(
                f"[{self.queue_name}] Max retries exceeded → sending to DLQ"
            )

    @abstractmethod
    async def handle_event(self, event_type: str, body: dict) -> None:
        """Subclasses implement this. Raise any exception to trigger retry."""
        ...