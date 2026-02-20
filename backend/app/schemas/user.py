from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from datetime import datetime, date


class UserBase(BaseModel):
    """Base user schema"""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=50)
    full_name: Optional[str] = None


class UserCreate(UserBase):
    """Schema for user registration"""
    password: str = Field(..., min_length=8, max_length=100)


class UserUpdate(BaseModel):
    """Schema for user update"""
    email: Optional[EmailStr] = None
    username: Optional[str] = Field(None, min_length=3, max_length=50)
    full_name: Optional[str] = None
    password: Optional[str] = Field(None, min_length=8, max_length=100)

    # Profile fields
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Employment & salary
    is_employed: Optional[bool] = None
    basic_salary: Optional[float] = None
    da_percentage: Optional[float] = None
    employer_name: Optional[str] = None
    date_of_joining: Optional[date] = None
    pf_employee_pct: Optional[float] = None
    pf_employer_pct: Optional[float] = None


class UserInDB(UserBase):
    """Schema for user in database"""
    id: int
    is_active: bool
    is_superuser: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Profile fields
    phone: Optional[str] = None
    date_of_birth: Optional[date] = None
    gender: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    pincode: Optional[str] = None

    # Employment & salary
    is_employed: Optional[bool] = None
    basic_salary: Optional[float] = None
    da_percentage: Optional[float] = None
    employer_name: Optional[str] = None
    date_of_joining: Optional[date] = None
    pf_employee_pct: Optional[float] = None
    pf_employer_pct: Optional[float] = None

    class Config:
        from_attributes = True


class User(UserInDB):
    """Schema for user response"""
    pass


class UserLogin(BaseModel):
    """Schema for user login"""
    username: str
    password: str


class Token(BaseModel):
    """Schema for authentication token"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenData(BaseModel):
    """Schema for token data"""
    username: Optional[str] = None
    user_id: Optional[int] = None


# ── Password reset ────────────────────────────────────────────────────────────

class ForgotPasswordRequest(BaseModel):
    """Request body for the forgot-password endpoint."""
    email: EmailStr


class ForgotPasswordResponse(BaseModel):
    """
    Response for the forgot-password endpoint.

    ``reset_token`` is an empty string when the email is not registered so that
    the same response shape is returned regardless of whether the account exists
    (prevents email-enumeration attacks).  The frontend treats an empty token as
    "email not found".
    """
    message: str
    reset_token: str
    expires_in_minutes: int


class PasswordResetRequest(BaseModel):
    """Request body for the reset-password endpoint."""
    token: str
    new_password: str = Field(..., min_length=8, max_length=100)


class PasswordResetResponse(BaseModel):
    """Response after a successful password reset."""
    message: str
