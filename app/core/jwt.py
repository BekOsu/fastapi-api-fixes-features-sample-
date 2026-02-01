"""JWT token creation and validation."""

from datetime import datetime, timedelta, timezone

from jose import JWTError, jwt

from app.core.config import settings

ALGORITHM = settings.algorithm


class TokenError(Exception):
    """Raised when token validation fails."""

    pass


def create_access_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT access token.

    Args:
        subject: The subject (typically user ID) to encode in the token.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT token string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.access_token_expire_minutes
        )

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "access",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def create_refresh_token(subject: str | int, expires_delta: timedelta | None = None) -> str:
    """Create a JWT refresh token.

    Args:
        subject: The subject (typically user ID) to encode in the token.
        expires_delta: Optional custom expiration time.

    Returns:
        Encoded JWT refresh token string.
    """
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)

    to_encode = {
        "sub": str(subject),
        "exp": expire,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=ALGORITHM)


def decode_token(token: str) -> dict:
    """Decode and validate a JWT token.

    Args:
        token: The JWT token string to decode.

    Returns:
        Dictionary containing the token payload.

    Raises:
        TokenError: If the token is invalid or expired.
    """
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[ALGORITHM])
        return payload
    except JWTError as e:
        raise TokenError(f"Invalid token: {e}") from e


def decode_access_token(token: str) -> dict:
    """Decode and validate an access token.

    Args:
        token: The JWT access token string.

    Returns:
        Dictionary containing the token payload.

    Raises:
        TokenError: If the token is invalid, expired, or not an access token.
    """
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise TokenError("Not an access token")
    return payload


def decode_refresh_token(token: str) -> dict:
    """Decode and validate a refresh token.

    Args:
        token: The JWT refresh token string.

    Returns:
        Dictionary containing the token payload.

    Raises:
        TokenError: If the token is invalid, expired, or not a refresh token.
    """
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise TokenError("Not a refresh token")
    return payload
