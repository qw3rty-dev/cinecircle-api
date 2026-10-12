import os
from datetime import UTC, datetime, timedelta

import jwt
from dotenv import load_dotenv
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.models import User

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = os.getenv("ALGORITHM")

if not SECRET_KEY:
    raise ValueError("SECRET_KEY environment variable is not set")
if not ALGORITHM:
    raise ValueError("SECRET_KEY environment variable is not set")

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/v1/auth/login")
oauth2_scheme_optional = OAuth2PasswordBearer(
    tokenUrl="/v1/auth/login", auto_error=False
)


def create_token_access(user_id: int):
    expire = datetime.now(UTC) + timedelta(minutes=30)
    payload = {"sub": str(user_id), "exp": expire}

    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


def verify_token_access(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, [ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid access token"
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    user_id = int(sub)
    return user_id


async def get_current_user(
    token: str = Depends(oauth2_scheme), db: AsyncSession = Depends(get_db)
):
    current_user_id = verify_token_access(token)
    current_user = await db.scalar(
        select(User).where(User.id == current_user_id, User.is_deleted.is_(False))
    )
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return current_user


async def get_current_user_optional(
    token: str = Depends(oauth2_scheme_optional), db: AsyncSession = Depends(get_db)
):
    if not token:
        return None
    current_user_id = verify_token_access(token)
    current_user = await db.scalar(
        select(User).where(User.id == current_user_id, User.is_deleted.is_(False))
    )
    if not current_user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
        )
    return current_user


async def get_current_admin(current_user: User = Depends(get_current_user)):

    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Admin privileges required"
        )
    return current_user


def get_current_verified_user(current_user: User = Depends(get_current_user)):

    if not current_user.is_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Please verify your email to use this feature.",
        )
    return current_user


def create_refresh_token(user_id: int):
    expire = datetime.now(UTC) + timedelta(days=7)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, ALGORITHM)


def verify_refresh_token(token: str):
    try:
        payload = jwt.decode(token, SECRET_KEY, [ALGORITHM])
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
        )
    sub = payload.get("sub")
    if not sub:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized"
        )
    user_id = int(sub)
    return user_id
