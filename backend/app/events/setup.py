import logging
from aio_pika import ExchangeType
from app.events.connection import rabbitmq_manager
from app.events import exchanges as ex

logger = logging.getLogger(__name__)


async def declare_topology() -> None:
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

    # ── 4. Main queues ─────────────────────────────────────────────────────
    queue_configs = [
        (ex.QUEUE_TASK_NOTIFICATIONS, "task.*", ex.DLQ_TASK_NOTIFICATIONS),
        (ex.QUEUE_TASK_AUDIT,         "task.*", ex.DLQ_TASK_AUDIT),
        (ex.QUEUE_TASK_ANALYTICS,     "task.*", ex.DLQ_TASK_ANALYTICS),
    ]

    for queue_name, routing_pattern, dlq_name in queue_configs:
        queue = await channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-dead-letter-exchange":    ex.DLX_EXCHANGE,
                "x-dead-letter-routing-key": dlq_name,
                "x-message-ttl":             86_400_000,
            },
        )
        await queue.bind(task_exchange, routing_key=routing_pattern)
        logger.info(f"Queue declared and bound: {queue_name} ← {routing_pattern}")

    # ── 5. Retry exchange (direct) ─────────────────────────────────────────
    retry_exchange = await channel.declare_exchange(
        ex.RETRY_EXCHANGE,
        ExchangeType.DIRECT,
        durable=True,
    )

    # ── 6. Delay queues — one per retry attempt per main queue ─────────────
    for queue_name in (
        ex.QUEUE_TASK_NOTIFICATIONS,
        ex.QUEUE_TASK_AUDIT,
        ex.QUEUE_TASK_ANALYTICS,
    ):
        for attempt, delay_ms in enumerate(ex.RETRY_DELAYS_MS, start=1):
            delay_queue_name = ex.retry_queue_name(queue_name, attempt)

            # Messages sit here until TTL expires, then route back to
            # the original queue via DLX
            delay_queue = await channel.declare_queue(
                delay_queue_name,
                durable=True,
                arguments={
                    "x-message-ttl":             delay_ms,
                    "x-dead-letter-exchange":    "",        # default exchange
                    "x-dead-letter-routing-key": queue_name, # back to original
                },
            )
            await delay_queue.bind(
                retry_exchange,
                routing_key=delay_queue_name,
            )
            logger.info(
                f"Delay queue declared: {delay_queue_name} "
                f"(TTL={delay_ms}ms → {queue_name})"
            )

    await channel.close()
    logger.info("RabbitMQ topology declared ✓")