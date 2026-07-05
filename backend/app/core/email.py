import logging

logger = logging.getLogger(__name__)


def send_verification_email(email: str, token: str) -> None:
    """
    Send email verification link.
    Currently logs to console — swap this for SendGrid/SMTP in production.
    """
    link = f"http://localhost:8000/api/v1/auth/verify-email?token={token}"
    logger.info(
        f"[EMAIL] Verification email for {email}\n"
        f"  Link: {link}\n"
        f"  (In production this would be sent via SMTP/SendGrid)"
    )


def send_password_reset_email(email: str, token: str) -> None:
    """
    Send password reset link.
    Currently logs to console — swap this for SendGrid/SMTP in production.
    """
    link = f"http://localhost:8000/api/v1/auth/reset-password?token={token}"
    logger.info(
        f"[EMAIL] Password reset email for {email}\n"
        f"  Link: {link}\n"
        f"  (In production this would be sent via SMTP/SendGrid)"
    )