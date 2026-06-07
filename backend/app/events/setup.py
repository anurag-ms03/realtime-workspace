import logging
import aio_pika
from aio_pika import ExchangeType
from app.events.connection import rabbitmq_manager
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


async def declare_topology() -> None:
    """
    Declares exchanges, queues, and bindings.
    Called once at startup after rabbitmq_manager.connect().
    All declarations are durable and idempotent.
    """
    channel = await rabbitmq_manager.get_channel()

    # ── 1. Dead-letter exchange (direct) ───────────────────────────────────
    dlx = await channel.declare_exchange(
        ex.DLX_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )

    # ── 2. Dead-letter queues ──────────────────────────────────────────────
    for dlq_name in (
        ex.DLQ_TASK_NOTIFICATIONS,
        ex.DLQ_TASK_AUDIT,
        ex.DLQ_TASK_ANALYTICS,
    ):
        dlq = await channel.declare_queue(dlq_name, durable=True)
        await dlq.bind(dlx, routing_key=dlq_name)

    # ── 3. Main task-events exchange (topic) ───────────────────────────────
    task_exchange = await channel.declare_exchange(
        ex.TASK_EVENTS_EXCHANGE,
        ExchangeType.TOPIC,
        durable=True,
    )

    # ── 4. Main queues — each bound with a routing key pattern ─────────────
    queue_configs = [
        # (queue_name,                    routing_pattern, dlq_name)
        (ex.QUEUE_TASK_NOTIFICATIONS, "task.*",        ex.DLQ_TASK_NOTIFICATIONS),
        (ex.QUEUE_TASK_AUDIT,         "task.*",        ex.DLQ_TASK_AUDIT),
        (ex.QUEUE_TASK_ANALYTICS,     "task.*",        ex.DLQ_TASK_ANALYTICS),
    ]

    for queue_name, routing_pattern, dlq_name in queue_configs:
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange":    ex.DLX_EXCHANGE,
                "x-dead-letter-routing-key": dlq_name,
                "x-message-ttl":             86_400_000,   # 24 h in ms
            },
        )
        await queue.bind(task_exchange, routing_key=routing_pattern)
        logger.info(f"Queue declared and bound: {queue_name} ← {routing_pattern}")

    await channel.close()
    logger.info("RabbitMQ topology declared ✓")