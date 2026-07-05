import secrets
import redis
from app.core.config import settings

_redis = redis.from_url(settings.REDIS_URL, decode_responses=True)

VERIFICATION_TOKEN_TTL = 86_400      # 24 hours
RESET_TOKEN_TTL        = 3_600       # 1 hour

VERIFY_PREFIX = "email_verify:"
RESET_PREFIX  = "password_reset:"


# ── Email verification ─────────────────────────────────────────────────────

def create_verification_token(user_id: str) -> str:
    """Generate a secure random token and store user_id in Redis."""
    token = secrets.token_urlsafe(32)
    _redis.setex(f"{VERIFY_PREFIX}{token}", VERIFICATION_TOKEN_TTL, user_id)
    return token


def verify_email_token(token: str) -> str | None:
    """
    Validate token and return user_id if valid.
    Deletes token after use — single use only.
    """
    key = f"{VERIFY_PREFIX}{token}"
    user_id = _redis.get(key)
    if user_id:
        _redis.delete(key)   # single use
    return user_id


# ── Password reset ─────────────────────────────────────────────────────────

def create_reset_token(user_id: str) -> str:
    """Generate a secure random token and store user_id in Redis."""
    token = secrets.token_urlsafe(32)
    _redis.setex(f"{RESET_PREFIX}{token}", RESET_TOKEN_TTL, user_id)
    return token


def verify_reset_token(token: str) -> str | None:
    """
    Validate token and return user_id if valid.
    Does NOT delete — deletion happens after password is successfully changed.
    """
    key = f"{RESET_PREFIX}{token}"
    return _redis.get(key)


def consume_reset_token(token: str) -> None:
    """Delete reset token after successful password change."""
    _redis.delete(f"{RESET_PREFIX}{token}")