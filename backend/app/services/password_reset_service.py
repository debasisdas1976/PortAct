"""
Password reset token service.

Uses a signed JWT that embeds a fingerprint of the user's current hashed_password.
This ensures the token self-invalidates the moment the password is changed,
with no database schema changes required.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from sqlalchemy.orm import Session
from loguru import logger

from app.core.config import settings
from app.models.user import User

# Number of characters from hashed_password used as the fingerprint.
_FINGERPRINT_LEN = 16
_TOKEN_TYPE = "password_reset"


def create_password_reset_token(user: User) -> str:
    """
    Create a short-lived JWT for password reset.

    The token embeds a fingerprint of the user's current hashed_password so that
    it is automatically invalidated the moment the password is changed.
    """
    expire = datetime.now(timezone.utc) + timedelta(
        minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES
    )
    payload = {
        "sub": user.username,
        "user_id": user.id,
        "email": user.email,
        "fingerprint": user.hashed_password[:_FINGERPRINT_LEN],
        "type": _TOKEN_TYPE,
        "exp": expire,
    }
    return jwt.encode(payload, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def verify_password_reset_token(token: str, db: Session) -> Optional[User]:
    """
    Verify a password reset token and return the associated User if valid.

    Returns None if:
    - Token is malformed or expired (JWT error)
    - Token type is not 'password_reset'
    - User does not exist or is inactive
    - Password fingerprint does not match (token already used or password changed)
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
    except JWTError as exc:
        logger.debug(f"Password reset token decode failed: {exc}")
        return None

    if payload.get("type") != _TOKEN_TYPE:
        logger.debug("Password reset token has wrong type.")
        return None

    user_id = payload.get("user_id")
    fingerprint = payload.get("fingerprint")

    if user_id is None or fingerprint is None:
        logger.debug("Password reset token missing required claims.")
        return None

    user: Optional[User] = db.query(User).filter(User.id == user_id).first()

    if user is None or not user.is_active:
        logger.debug(f"Password reset token references missing/inactive user id={user_id}.")
        return None

    # Verify the password has not been changed since the token was issued.
    if user.hashed_password[:_FINGERPRINT_LEN] != fingerprint:
        logger.debug(f"Password reset token fingerprint mismatch for user id={user_id}.")
        return None

    return user
