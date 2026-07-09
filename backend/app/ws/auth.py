from typing import Optional
from sqlalchemy.orm import Session
from app.core.security import decode_token
from app.core.token_blacklist import is_blacklisted
from app.services.user import get_user_by_id
from app.models.user import User


def authenticate_ws_token(token: str, db: Session) -> Optional[User]:
    """
    Validates a JWT for a WebSocket connection. Mirrors deps.get_current_user
    but returns None instead of raising HTTPException, since WS rejection
    is handled via close code, not HTTP status.
    """
    payload = decode_token(token)
    if not payload or payload.get("type") != "access":
        return None

    jti = payload.get("jti")
    if not jti or is_blacklisted(jti):
        return None

    user_id = payload.get("sub")
    if not user_id:
        return None

    user = get_user_by_id(db, user_id)
    if not user or not user.is_active:
        return None

    return user