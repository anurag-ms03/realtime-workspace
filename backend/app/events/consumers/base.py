import json
import logging
from abc import ABC, abstractmethod
import aio_pika
from aio_pika.abc import AbstractIncomingMessage
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


class BaseConsumer(ABC):
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
        next_retry = retry_count + 1

        if next_retry < self.MAX_RETRIES:
            delay_ms = ex.RETRY_DELAYS_MS[retry_count]  # 2s, 4s, 8s
            delay_queue = ex.retry_queue_name(self.queue_name, next_retry)

            # Publish to delay queue — it will TTL back to original queue
            retry_exchange = await self._channel.get_exchange(ex.RETRY_EXCHANGE)
            await retry_exchange.publish(
                aio_pika.Message(
                    body=message.body,
                    content_type="application/json",
                    delivery_mode=aio_pika.DeliveryMode.PERSISTENT,
                    headers={
                        **dict(message.headers),
                        "x-retry-count": next_retry,
                        "x-last-error":  str(error),
                    },
                ),
                routing_key=delay_queue,
            )
            await message.ack()
            logger.warning(
                f"[{self.queue_name}] Retry {next_retry}/{self.MAX_RETRIES} "
                f"scheduled in {delay_ms}ms via {delay_queue}"
            )

        else:
            # Max retries exceeded → DLQ via nack
            await message.nack(requeue=False)
            logger.error(
                f"[{self.queue_name}] Max retries exceeded → sending to DLQ"
            )

    @abstractmethod
    async def handle_event(self, event_type: str, body: dict) -> None:
        ...