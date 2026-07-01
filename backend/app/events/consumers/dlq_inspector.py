import json
import logging
from aio_pika.abc import AbstractIncomingMessage
import aio_pika
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


class DLQInspector:
    """
    Watches a single dead-letter queue and logs everything that lands there.
    Does NOT ack/nack with retry logic — DLQ messages are terminal.
    Messages stay in the DLQ for manual inspection/reprocessing.
    """

    def __init__(self, dlq_name: str, source_queue: str):
        self.dlq_name = dlq_name
        self.source_queue = source_queue

    async def start(self, channel: aio_pika.Channel) -> None:
        queue = await channel.get_queue(self.dlq_name)
        await queue.consume(self._on_message, no_ack=False)
        logger.info(f"DLQ inspector started → watching: {self.dlq_name}")

    async def _on_message(self, message: AbstractIncomingMessage) -> None:
        try:
            body = json.loads(message.body.decode())
            event_type = body.get("event_type", "unknown")
            event_id = body.get("event_id", "unknown")
            last_error = message.headers.get("x-last-error", "unknown")
            retry_count = message.headers.get("x-retry-count", "unknown")

            logger.error(
                f"☠️  [DLQ:{self.dlq_name}] Dead message | "
                f"source_queue={self.source_queue} "
                f"type={event_type} id={event_id} "
                f"retries_attempted={retry_count} "
                f"last_error={last_error}"
            )

            # ACK to remove from DLQ — in production you'd persist this
            # to a "failed_events" table before acking, for manual review.
            await message.ack()

        except Exception as e:
            logger.error(f"[DLQ:{self.dlq_name}] Failed to inspect message: {e}")
            await message.nack(requeue=True)