import logging
import redis.asyncio as aioredis
from app.core.config import settings

logger = logging.getLogger(__name__)

# TTL for processed event IDs — 24 hours is enough to cover any retry window
IDEMPOTENCY_TTL_SECONDS = 86_400

# Async Redis client — separate from the sync one used elsewhere
_redis: aioredis.Redis = None


def get_redis() -> aioredis.Redis:
    global _redis
    if _redis is None:
        _redis = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
    return _redis


async def is_duplicate(event_id: str, consumer_name: str) -> bool:
    """
    Returns True if this event_id was already processed by this consumer.
    Uses a per-consumer key so the same event can be processed independently
    by each consumer (notifications, audit, analytics) without interference.
    """
    key = f"processed_event:{consumer_name}:{event_id}"
    redis = get_redis()

    # SET NX (only set if not exists) — atomic check-and-set
    result = await redis.set(key, "1", ex=IDEMPOTENCY_TTL_SECONDS, nx=True)

    if result is None:
        # Key already existed — this is a duplicate
        logger.warning(
            f"[IDEMPOTENCY] Duplicate event skipped | "
            f"consumer={consumer_name} event_id={event_id}"
        )
        return True

    return False


async def clear_event(event_id: str, consumer_name: str) -> None:
    """
    Remove an event from the processed set — used when we want to allow
    reprocessing (e.g. after a bug fix, manual replay from DLQ).
    """
    key = f"processed_event:{consumer_name}:{event_id}"
    await get_redis().delete(key)
    logger.info(f"[IDEMPOTENCY] Cleared event | consumer={consumer_name} event_id={event_id}")