from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from app.models.user import User
from app.schemas.user import UserCreate
from app.core.security import hash_password
from app.core.verification import create_verification_token, verify_email_token
from app.core.email import send_verification_email


def get_user_by_email(db: Session, email: str):
    return db.query(User).filter(User.email == email).first()


def get_user_by_username(db: Session, username: str):
    return db.query(User).filter(User.username == username).first()


def get_user_by_id(db: Session, user_id):
    return db.query(User).filter(User.id == user_id).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    if get_user_by_email(db, user_data.email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    if get_user_by_username(db, user_data.username):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )

    user = User(
        email=user_data.email,
        username=user_data.username,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # ── Send verification email ────────────────────────────────────────────
    token = create_verification_token(str(user.id))
    send_verification_email(user.email, token)

    return user


def verify_user_email(db: Session, token: str) -> User:
    """Validate token, mark user as verified, return updated user."""
    user_id = verify_email_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    if user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already verified",
        )

    user.is_verified = True
    db.commit()
    db.refresh(user)
    return user


def request_password_reset(db: Session, email: str) -> None:
    """
    Generate reset token and send email.
    Always returns success even if email not found — prevents user enumeration.
    """
    from app.core.verification import create_reset_token
    from app.core.email import send_password_reset_email

    user = get_user_by_email(db, email)
    if user:
        token = create_reset_token(str(user.id))
        send_password_reset_email(user.email, token)


def reset_user_password(db: Session, token: str, new_password: str) -> None:
    """Validate reset token, update password, consume token."""
    from app.core.verification import verify_reset_token, consume_reset_token

    user_id = verify_reset_token(token)
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )

    user = get_user_by_id(db, user_id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    user.hashed_password = hash_password(new_password)
    db.commit()
    consume_reset_token(token)