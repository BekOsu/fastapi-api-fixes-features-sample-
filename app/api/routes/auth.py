"""Authentication endpoints."""

from fastapi import APIRouter, status

from app.api.deps import CurrentUser, DBSession
from app.schemas.user import (
    RefreshTokenRequest,
    TokenResponse,
    UserCreate,
    UserLogin,
    UserResponse,
)
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    response_model=TokenResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
)
def register(user_data: UserCreate, db: DBSession) -> TokenResponse:
    """Register a new user account.

    Returns access and refresh tokens upon successful registration.
    """
    _, tokens = auth_service.register(db, user_data)
    return tokens


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Login with email and password",
)
def login(credentials: UserLogin, db: DBSession) -> TokenResponse:
    """Authenticate with email and password.

    Returns access and refresh tokens upon successful authentication.
    """
    _, tokens = auth_service.login(db, credentials.email, credentials.password)
    return tokens


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Refresh access token",
)
def refresh(request: RefreshTokenRequest, db: DBSession) -> TokenResponse:
    """Get new access and refresh tokens using a valid refresh token."""
    return auth_service.refresh_tokens(db, request.refresh_token)


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user",
)
def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get the currently authenticated user's information."""
    return UserResponse.model_validate(current_user)
