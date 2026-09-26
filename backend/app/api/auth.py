"""Authentication API endpoints."""

from fastapi import APIRouter, HTTPException, status

from app.api.deps import DB, CurrentUser
from app.schemas.user import Token, TokenRefresh, UserCreate, UserLogin, UserResponse
from app.services.auth import (
    authenticate_user,
    create_tokens,
    create_user,
    decode_token,
    get_user_by_email,
    get_user_by_id,
    get_user_by_username,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(data: UserCreate, db: DB) -> Token:
    """Register a new user."""
    # Check if email exists
    existing = await get_user_by_email(db, data.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    # Check if username exists
    existing = await get_user_by_username(db, data.username)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already taken",
        )
    
    # Create user
    user = await create_user(db, data)
    
    # Return tokens
    return create_tokens(user.id)


@router.post("/login", response_model=Token)
async def login(data: UserLogin, db: DB) -> Token:
    """Login with username and password."""
    user = await authenticate_user(db, data.username, data.password)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
        )
    
    return create_tokens(user.id)


@router.post("/refresh", response_model=Token)
async def refresh_token(data: TokenRefresh, db: DB) -> Token:
    """Refresh access token using refresh token."""
    payload = decode_token(data.refresh_token)
    
    if payload is None or payload.type != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    
    user = await get_user_by_id(db, payload.sub)
    
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    
    return create_tokens(user.id)


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(current_user: CurrentUser) -> UserResponse:
    """Get current user information."""
    return UserResponse.model_validate(current_user)


@router.post("/logout")
async def logout() -> dict:
    """Logout user (client should discard tokens)."""
    return {"message": "Successfully logged out"}
