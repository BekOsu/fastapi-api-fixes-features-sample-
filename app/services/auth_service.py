"""Authentication service for login, registration, and token management."""

from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.jwt import (
    TokenError,
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.db.models.user import User
from app.schemas.user import TokenResponse, UserCreate
from app.services.user_service import authenticate_user, create_user, get_user_by_id


def register(db: Session, user_data: UserCreate) -> tuple[User, TokenResponse]:
    """Register a new user and return tokens.

    Args:
        db: Database session.
        user_data: User registration data.

    Returns:
        Tuple of (User, TokenResponse).

    Raises:
        ConflictError: If the email is already taken.
    """
    user = create_user(db, user_data)
    tokens = _create_tokens(user.id)
    return user, tokens


def login(db: Session, email: str, password: str) -> tuple[User, TokenResponse]:
    """Authenticate a user and return tokens.

    Args:
        db: Database session.
        email: User's email address.
        password: User's password.

    Returns:
        Tuple of (User, TokenResponse).

    Raises:
        UnauthorizedError: If credentials are invalid.
    """
    user = authenticate_user(db, email, password)
    if not user:
        raise UnauthorizedError("Invalid email or password")

    tokens = _create_tokens(user.id)
    return user, tokens


def refresh_tokens(db: Session, refresh_token: str) -> TokenResponse:
    """Refresh access and refresh tokens.

    Args:
        db: Database session.
        refresh_token: The current refresh token.

    Returns:
        New TokenResponse with fresh tokens.

    Raises:
        UnauthorizedError: If the refresh token is invalid.
    """
    try:
        payload = decode_refresh_token(refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid refresh token")
    except TokenError as e:
        raise UnauthorizedError(str(e))

    # Verify user still exists and is active
    try:
        user = get_user_by_id(db, int(user_id))
    except Exception:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return _create_tokens(user.id)


def _create_tokens(user_id: int) -> TokenResponse:
    """Create access and refresh tokens for a user.

    Args:
        user_id: The user's ID.

    Returns:
        TokenResponse with both tokens.
    """
    return TokenResponse(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )
