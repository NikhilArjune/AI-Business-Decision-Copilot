"""
AI Business Decision Copilot - Auth API Routes
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models.db_models import User, AuditLog
from ..schemas.api_schemas import UserRegister, UserLogin, UserResponse, TokenResponse
from ..core.security import hash_password, verify_password, create_access_token, get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/register", response_model=TokenResponse, status_code=201)
async def register(data: UserRegister, db: AsyncSession = Depends(get_db)):
    """Register a new user."""
    # Check existing
    result = await db.execute(select(User).where(User.email == data.email))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Email already registered")

    user = User(
        name=data.name,
        email=data.email,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    await db.flush()

    # Audit log
    db.add(AuditLog(user_id=user.id, action="user_registered", resource_type="user", resource_id=user.id))

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    logger.info(f"User registered: {user.email} (role: {user.role})")
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, name=user.name, email=user.email,
            role=user.role, created_at=user.created_at,
        ),
    )


@router.post("/login", response_model=TokenResponse)
async def login(data: UserLogin, db: AsyncSession = Depends(get_db)):
    """Login with email and password."""
    result = await db.execute(select(User).where(User.email == data.email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(data.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role})

    # Audit log
    db.add(AuditLog(user_id=user.id, action="user_login", resource_type="user", resource_id=user.id))

    logger.info(f"User logged in: {user.email}")
    return TokenResponse(
        access_token=token,
        user=UserResponse(
            id=user.id, name=user.name, email=user.email,
            role=user.role, created_at=user.created_at,
        ),
    )


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current user profile."""
    result = await db.execute(select(User).where(User.id == current_user["user_id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user
