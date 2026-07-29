import json
import logging
import time
import redis
from app.core.celery_app import celery_app
from app.core.config import settings

logger = logging.getLogger(__name__)

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

COUNTERS_KEY_PATTERN = "analytics:*:counters"


@celery_app.task(
    name="rollup_task_analytics",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=120,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=60,
    time_limit=90,
)
def rollup_task_analytics() -> dict:
    """
    Snapshots current per-workspace counters (maintained live by
    TaskAnalyticsConsumer) into a timestamped history list, so past
    counts are preserved even as the live counters keep incrementing.
    Discovers workspaces dynamically via Redis key scan — no hardcoded
    workspace list needed.
    """
    snapshot_time = int(time.time())
    rolled_up = []

    for key in _redis.scan_iter(match=COUNTERS_KEY_PATTERN):
        workspace_id = key.split(":")[1]
        counts = _redis.hgetall(key)

        snapshot = {
            "timestamp": snapshot_time,
            "counts": {
                "task.created": int(counts.get("task.created", 0)),
                "task.updated": int(counts.get("task.updated", 0)),
                "task.completed": int(counts.get("task.completed", 0)),
            },
        }

        history_key = f"analytics:{workspace_id}:snapshots"
        _redis.rpush(history_key, json.dumps(snapshot))

        rolled_up.append({"workspace_id": workspace_id, **snapshot})
        logger.info(f"[ANALYTICS ROLLUP] workspace={workspace_id} snapshot={snapshot}")

    if not rolled_up:
        logger.info("[ANALYTICS ROLLUP] No workspace counters found to roll up")

    return {"rolled_up_count": len(rolled_up), "snapshots": rolled_up}