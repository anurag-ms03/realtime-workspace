import redis
from app.core.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

BLACKLIST_PREFIX = "blacklisted_jti:"


def blacklist_token(jti: str, ttl_seconds: int) -> None:
    """Add a token's jti to the blacklist with TTL matching token expiry."""
    if ttl_seconds > 0:
        _redis.setex(f"{BLACKLIST_PREFIX}{jti}", ttl_seconds, "1")


def is_blacklisted(jti: str) -> bool:
    """Returns True if this jti has been blacklisted (i.e. logged out)."""
    return _redis.exists(f"{BLACKLIST_PREFIX}{jti}") == 1