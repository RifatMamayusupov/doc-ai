"""User schemas for authentication."""

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field


class UserCreate(BaseModel):
    """Schema for user registration."""
    email: EmailStr
    username: str = Field(..., min_length=3, max_length=100)
    password: str = Field(..., min_length=8)
    full_name: str | None = None


class UserLogin(BaseModel):
    """Schema for user login."""
    username: str
    password: str


class UserResponse(BaseModel):
    """Schema for user response."""
    id: str
    email: str
    username: str
    full_name: str | None = None
    avatar_url: str | None = None
    is_active: bool
    memory_enabled: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT tokens."""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class TokenPayload(BaseModel):
    """Schema for token payload."""
    sub: str  # user_id
    exp: datetime
    type: str  # "access" or "refresh"


class TokenRefresh(BaseModel):
    """Schema for token refresh request."""
    refresh_token: str
