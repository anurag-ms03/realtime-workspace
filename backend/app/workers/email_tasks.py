import logging
from app.core.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    name="send_verification_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,       # 1s, 2s, 4s... exponential
    retry_backoff_max=60,     # cap backoff at 60s
    retry_jitter=True,        # add randomness to avoid thundering herd
    max_retries=3,
    soft_time_limit=10,       # raises SoftTimeLimitExceeded inside the task
    time_limit=15,            # hard-kills the task if it's still running
)
def send_verification_email_task(email: str, token: str) -> None:
    link = f"http://localhost:8000/api/v1/auth/verify-email?token={token}"
    logger.info(
        f"[EMAIL] Verification email for {email}\n"
        f"  Link: {link}\n"
        f"  (In production this would be sent via SMTP/SendGrid)"
    )


@celery_app.task(
    name="send_password_reset_email_task",
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=60,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=10,
    time_limit=15,
)
def send_password_reset_email_task(email: str, token: str) -> None:
    link = f"http://localhost:8000/api/v1/auth/reset-password?token={token}"
    logger.info(
        f"[EMAIL] Password reset email for {email}\n"
        f"  Link: {link}\n"
        f"  (In production this would be sent via SMTP/SendGrid)"
    )