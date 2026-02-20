from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from sqlalchemy.exc import SQLAlchemyError
from loguru import logger
from app.core.database import get_db
from app.core.security import verify_password, get_password_hash, create_access_token, create_refresh_token
from app.core.config import settings
from app.models.user import User
from app.schemas.user import (
    UserCreate,
    User as UserSchema,
    Token,
    ForgotPasswordRequest,
    ForgotPasswordResponse,
    PasswordResetRequest,
    PasswordResetResponse,
)
from app.services.password_reset_service import (
    create_password_reset_token,
    verify_password_reset_token,
)

router = APIRouter()


@router.post("/register", response_model=UserSchema, status_code=status.HTTP_201_CREATED)
async def register(user_data: UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user
    """
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.email == user_data.email) | (User.username == user_data.username)
    ).first()
    
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User with this email or username already exists"
        )
    
    # Create new user
    new_user = User(
        email=user_data.email,
        username=user_data.username,
        full_name=user_data.full_name,
        hashed_password=get_password_hash(user_data.password),
        is_active=True,
        is_superuser=False
    )
    
    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    
    return new_user


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get access token
    """
    # Find user by username or email
    user = db.query(User).filter(
        (User.username == form_data.username) | (User.email == form_data.username)
    ).first()
    
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    # Create tokens
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer"
    }


@router.post("/refresh", response_model=Token)
async def refresh_token(
    refresh_token: str,
    db: Session = Depends(get_db)
):
    """
    Refresh access token using refresh token
    """
    from app.core.security import decode_token
    
    payload = decode_token(refresh_token)
    if payload is None or payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token"
        )
    
    username = payload.get("sub")
    user = db.query(User).filter(User.username == username).first()
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user"
        )
    
    # Create new tokens
    access_token = create_access_token(
        data={"sub": user.username, "user_id": user.id}
    )
    new_refresh_token = create_refresh_token(
        data={"sub": user.username, "user_id": user.id}
    )
    
    return {
        "access_token": access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }


# ---------------------------------------------------------------------------
# Password reset
# ---------------------------------------------------------------------------

@router.post("/forgot-password", response_model=ForgotPasswordResponse)
async def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Request a password reset token.

    Always returns HTTP 200 with the same shape to avoid leaking whether
    an email address is registered (email enumeration protection).
    When the email is not found ``reset_token`` is an empty string — the
    frontend uses this as the signal to show "email not found".
    """
    _NOT_FOUND = ForgotPasswordResponse(
        message="If that email is registered you will see a reset link below.",
        reset_token="",
        expires_in_minutes=0,
    )

    try:
        user: User | None = db.query(User).filter(User.email == request.email).first()
    except SQLAlchemyError as exc:
        logger.error(f"DB error in forgot-password for {request.email}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service temporarily unavailable. Please try again.",
        )

    if not user or not user.is_active:
        return _NOT_FOUND

    token = create_password_reset_token(user)
    logger.info(f"Password reset token created for user id={user.id}.")

    return ForgotPasswordResponse(
        message="Reset link generated. Use the button below to set a new password.",
        reset_token=token,
        expires_in_minutes=settings.PASSWORD_RESET_TOKEN_EXPIRE_MINUTES,
    )


@router.post("/reset-password", response_model=PasswordResetResponse)
async def reset_password(
    request: PasswordResetRequest,
    db: Session = Depends(get_db),
):
    """
    Reset the user's password using a valid reset token.

    The token is invalidated automatically once the password changes because
    the fingerprint embedded in the JWT will no longer match.
    """
    user = verify_password_reset_token(request.token, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired password reset link. Please request a new one.",
        )

    try:
        user.hashed_password = get_password_hash(request.new_password)
        db.commit()
        logger.info(f"Password reset successfully for user id={user.id}.")
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"DB error resetting password for user id={user.id}: {exc}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Failed to update password. Please try again.",
        )

    return PasswordResetResponse(message="Password updated successfully. You can now log in.")
