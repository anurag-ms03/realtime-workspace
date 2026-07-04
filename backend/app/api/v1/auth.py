from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.token_blacklist import blacklist_token
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Annotated
from app.api.deps import get_db, get_current_user
from app.schemas.user import (
    UserCreate, UserResponse, TokenResponse, LoginRequest, RefreshRequest, MessageResponse
)
from app.services.user import create_user, get_user_by_email
from app.core.security import (
    verify_password, create_access_token, create_refresh_token, decode_token, get_token_remaining_ttl
)
from app.models.user import User

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=UserResponse, status_code=201)
def register(user_data: UserCreate, db: Session = Depends(get_db)):
    return create_user(db, user_data)


@router.post("/login", response_model=TokenResponse)
def login(credentials: LoginRequest, db: Session = Depends(get_db)):
    user = get_user_by_email(db, credentials.email)

    if not user or not verify_password(credentials.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is disabled",
        )

    token_data = {"sub": str(user.id)}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(request: RefreshRequest):
    payload = decode_token(request.refresh_token)

    if not payload or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token",
        )

    token_data = {"sub": payload.get("sub")}
    return TokenResponse(
        access_token=create_access_token(token_data),
        refresh_token=create_refresh_token(token_data),
    )

bearer_scheme = HTTPBearer()

@router.post("/logout", response_model=MessageResponse)
def logout(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(bearer_scheme)],
    current_user: User = Depends(get_current_user),
):
    token = credentials.credentials
    payload = decode_token(token)
    if payload:
        jti = payload.get("jti")
        ttl = get_token_remaining_ttl(payload)
        if jti:
            blacklist_token(jti, ttl)
    return MessageResponse(message="Successfully logged out")

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    return current_user