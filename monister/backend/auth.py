"""
Monister Auth - JWT authentication and password hashing.
"""

import os
from datetime import datetime, timedelta
from typing import Optional
from passlib.context import CryptContext
from jose import JWTError, jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr

from database import get_db, User

# JWT Settings
JWT_SECRET = os.getenv("JWT_SECRET", "monister-super-secret-key-change-in-production")
JWT_ALGORITHM = "HS256"
JWT_EXPIRE_MINUTES = 60 * 24  # 24 hours

# Password hashing - using pbkdf2_sha256 (no external dependency issues)
pwd_context = CryptContext(schemes=["pbkdf2_sha256"], deprecated="auto")

# Bearer token scheme
security = HTTPBearer(auto_error=False)


# Pydantic models
class UserCreate(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: dict


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    is_admin: bool
    created_at: Optional[str]


class ProfileUpdate(BaseModel):
    telegram_username: Optional[str] = None
    email: Optional[str] = None


# Password functions
def hash_password(password: str) -> str:
    """Hash a password."""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a password against its hash."""
    return pwd_context.verify(plain_password, hashed_password)


# JWT functions
def create_access_token(user_id: int, username: str, is_admin: bool = False) -> str:
    """Create a JWT access token."""
    expire = datetime.utcnow() + timedelta(minutes=JWT_EXPIRE_MINUTES)
    payload = {
        "sub": str(user_id),
        "username": username,
        "is_admin": is_admin,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def decode_token(token: str) -> Optional[dict]:
    """Decode and validate a JWT token."""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


# FastAPI Dependencies
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """Get current user from JWT token."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    token = credentials.credentials
    payload = decode_token(token)
    
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    user_id = payload.get("sub")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token payload",
        )
    
    user = db.query(User).filter(User.id == int(user_id)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="User is inactive",
        )
    
    return user


async def get_current_user_optional(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> Optional[User]:
    """Get current user if authenticated, otherwise None."""
    if not credentials:
        return None
    
    try:
        return await get_current_user(credentials, db)
    except HTTPException:
        return None


async def get_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Require admin user."""
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return current_user


# User CRUD functions
def create_user(db: Session, username: str, email: str, password: str, is_admin: bool = False) -> User:
    """Create a new user."""
    # Check if username exists
    if db.query(User).filter(User.username == username).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username already registered",
        )
    
    # Check if email exists
    if db.query(User).filter(User.email == email).first():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    
    user = User(
        username=username,
        email=email,
        password_hash=hash_password(password),
        is_admin=is_admin,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def authenticate_user(db: Session, username: str, password: str) -> Optional[User]:
    """Authenticate user by username and password."""
    user = db.query(User).filter(User.username == username).first()
    if not user:
        # Also try email
        user = db.query(User).filter(User.email == username).first()
    
    if not user or not verify_password(password, user.password_hash):
        return None
    
    # Update last login
    user.last_login = datetime.utcnow()
    db.commit()
    
    return user


def get_or_create_system_user(db: Session) -> User:
    """Get or create a system user for legacy files."""
    system_user = db.query(User).filter(User.username == "system").first()
    if not system_user:
        system_user = User(
            username="system",
            email="system@monister.local",
            password_hash=hash_password("system-internal-user"),
            is_admin=False,
            is_active=True,
        )
        db.add(system_user)
        db.commit()
        db.refresh(system_user)
    return system_user


def create_admin_if_not_exists(db: Session):
    """Create admin user from environment variables if not exists."""
    admin_username = os.getenv("ADMIN_USERNAME", "admin")
    admin_password = os.getenv("ADMIN_PASSWORD", "admin123")
    admin_email = os.getenv("ADMIN_EMAIL", "admin@monister.local")
    
    existing = db.query(User).filter(User.username == admin_username).first()
    if not existing:
        admin_user = User(
            username=admin_username,
            email=admin_email,
            password_hash=hash_password(admin_password),
            is_admin=True,
            is_active=True,
        )
        db.add(admin_user)
        db.commit()
        print(f"✅ Admin user '{admin_username}' created!")
    else:
        print(f"ℹ️ Admin user '{admin_username}' already exists.")


def update_user_profile(db: Session, user: User, profile: ProfileUpdate) -> User:
    """Update user profile fields (telegram_username, email)."""
    if profile.telegram_username is not None:
        # Clean telegram username
        tg_user = profile.telegram_username.strip().lstrip("@")
        user.telegram_username = tg_user if tg_user else None

    if profile.email is not None:
        # Check if email is already taken by another user
        existing = db.query(User).filter(
            User.email == profile.email,
            User.id != user.id
        ).first()
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already registered by another user",
            )
        user.email = profile.email

    db.commit()
    db.refresh(user)
    return user
