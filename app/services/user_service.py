"""User service for user-related operations."""

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError
from app.core.security import hash_password, verify_password
from app.db.models.user import User
from app.schemas.user import UserCreate, UserUpdate


def get_user_by_id(db: Session, user_id: int) -> User:
    """Get a user by ID.

    Args:
        db: Database session.
        user_id: The user's ID.

    Returns:
        The User object.

    Raises:
        NotFoundError: If the user doesn't exist.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise NotFoundError("User", user_id)
    return user


def get_user_by_email(db: Session, email: str) -> User | None:
    """Get a user by email address.

    Args:
        db: Database session.
        email: The user's email address.

    Returns:
        The User object if found, None otherwise.
    """
    return db.query(User).filter(User.email == email).first()


def create_user(db: Session, user_data: UserCreate) -> User:
    """Create a new user.

    Args:
        db: Database session.
        user_data: User creation data.

    Returns:
        The created User object.

    Raises:
        ConflictError: If a user with this email already exists.
    """
    existing_user = get_user_by_email(db, user_data.email)
    if existing_user:
        raise ConflictError(
            f"User with email '{user_data.email}' already exists",
            details={"email": user_data.email},
        )

    user = User(
        email=user_data.email,
        hashed_password=hash_password(user_data.password),
        full_name=user_data.full_name,
        is_active=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def update_user(db: Session, user: User, user_data: UserUpdate) -> User:
    """Update a user's information.

    Args:
        db: Database session.
        user: The user to update.
        user_data: Update data.

    Returns:
        The updated User object.
    """
    if user_data.full_name is not None:
        user.full_name = user_data.full_name

    if user_data.password is not None:
        user.hashed_password = hash_password(user_data.password)

    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, email: str, password: str) -> User | None:
    """Authenticate a user by email and password.

    Args:
        db: Database session.
        email: The user's email address.
        password: The plain text password.

    Returns:
        The User object if authentication succeeds, None otherwise.
    """
    user = get_user_by_email(db, email)
    if not user:
        return None
    if not verify_password(password, user.hashed_password):
        return None
    if not user.is_active:
        return None
    return user
