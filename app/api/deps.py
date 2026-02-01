"""FastAPI dependencies for authentication and database access."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from app.core.exceptions import UnauthorizedError
from app.core.jwt import TokenError, decode_access_token
from app.db.models.user import User
from app.db.session import SessionLocal

# Security scheme for JWT bearer tokens
security = HTTPBearer(auto_error=False)


def get_db() -> Generator[Session, None, None]:
    """Provide a database session for a request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Type alias for database dependency
DBSession = Annotated[Session, Depends(get_db)]


def get_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User:
    """Get the current authenticated user from the JWT token.

    Args:
        db: Database session.
        credentials: HTTP Bearer credentials from the Authorization header.

    Returns:
        The authenticated User object.

    Raises:
        UnauthorizedError: If the token is missing, invalid, or the user doesn't exist.
    """
    if not credentials:
        raise UnauthorizedError("Missing authentication token")

    try:
        payload = decode_access_token(credentials.credentials)
        user_id = payload.get("sub")
        if not user_id:
            raise UnauthorizedError("Invalid token payload")
    except TokenError as e:
        raise UnauthorizedError(str(e))

    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise UnauthorizedError("User not found")

    if not user.is_active:
        raise UnauthorizedError("User account is inactive")

    return user


# Type alias for current user dependency
CurrentUser = Annotated[User, Depends(get_current_user)]


def get_optional_current_user(
    db: DBSession,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(security)],
) -> User | None:
    """Get the current user if authenticated, otherwise return None.

    Useful for endpoints that work differently for authenticated vs anonymous users.
    """
    if not credentials:
        return None

    try:
        return get_current_user(db, credentials)
    except UnauthorizedError:
        return None


# Type alias for optional current user dependency
OptionalCurrentUser = Annotated[User | None, Depends(get_optional_current_user)]
