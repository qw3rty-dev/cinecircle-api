from datetime import UTC, datetime, timedelta

from fastapi import BackgroundTasks, HTTPException, status
from sqlalchemy import delete, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.enums import CodePurpose
from src.models import User
from src.security.jwt_handler import (
    create_refresh_token,
    create_token_access,
    verify_refresh_token,
)
from src.security.password import (
    hash_password,
    verification_code_generate,
    verify_password,
)
from src.services.email.service import send_password_reset_otp, send_verification_mail


class AuthService:
    async def register(
        self,
        username: str,
        email: str,
        password: str,
        is_private: bool,
        db: AsyncSession,
    ):

        username = username.strip().lower()
        email = email.strip().lower()

        existing_username = await db.scalar(
            select(User).where(User.username == username)
        )
        if existing_username:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Username already exists"
            )

        existing_email = await db.scalar(select(User).where(User.email == email))
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="Email already exists"
            )

        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_private=is_private,
        )
        try:
            db.add(new_user)
            await db.commit()
            await db.refresh(new_user)

        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already exists"
            )
        return new_user

    async def login(self, email: str, password: str, db: AsyncSession):

        user = await db.scalar(select(User).where(User.email == email))
        if not user or not verify_password(password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials"
            )
        if user.is_deleted:
            if user.deleted_at + timedelta(days=30) <= datetime.now(UTC):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid credentials",
                )
            user.is_deleted = False
            user.deleted_at = None

        access_token = create_token_access(user.id)
        refresh_token = create_refresh_token(user.id)
        user.last_login = datetime.now(UTC)
        user.refresh_token = hash_password(refresh_token)
        await db.commit()
        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def change_password(
        self, user: User, current_password: str, new_password: str, db: AsyncSession
    ):
        if not verify_password(current_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect current password",
            )
        user.password_hash = hash_password(new_password)
        user.refresh_token = None
        await db.commit()
        return {"message": "Password changed successfully"}

    async def refresh(self, refresh_token: str, db: AsyncSession):
        user_id = verify_refresh_token(refresh_token)
        user = await db.get(User, user_id)

        if (
            not user
            or not user.refresh_token
            or not verify_password(refresh_token, user.refresh_token)
        ):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token"
            )
        new_access_token = create_token_access(user.id)
        return {
            "access_token": new_access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
        }

    async def logout(self, current_user: User, db: AsyncSession):
        current_user.refresh_token = None
        await db.commit()
        return {"message": "Logged out successfully"}

    async def send_verification_code(
        self, background_tasks: BackgroundTasks, current_user: User, db: AsyncSession
    ):

        if current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already verified"
            )

        verification_code, expires_at = verification_code_generate()
        current_user.verification_code = hash_password(verification_code)
        current_user.verification_expires_at = expires_at
        current_user.code_purpose = CodePurpose.verification_otp
        await db.commit()
        background_tasks.add_task(
            send_verification_mail,
            current_user.username,
            current_user.email,
            verification_code,
        )

        return {"message": "Verification code sent"}

    async def confirm_verification_code(
        self, verification_otp: str, current_user: User, db: AsyncSession
    ):

        if current_user.is_verified:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT, detail="User already verified"
            )

        if not current_user.verification_expires_at or not current_user.code_purpose == CodePurpose.verification_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code",
            )

        if current_user.verification_expires_at < datetime.now(
            UTC
        ) or not verify_password(verification_otp, current_user.verification_code):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code",
            )

        current_user.is_verified = True
        current_user.verification_code = None
        current_user.verification_expires_at = None
        current_user.code_purpose = None
        await db.commit()

        return {"message": "Verification done"}

    async def forgot_password(
        self, email: str, background_tasks: BackgroundTasks, db: AsyncSession
    ):

        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            return {
                "message": "If an account with that email exists,a password reset email has been sent."
            }

        verification_code, expires_at = verification_code_generate()
        user.verification_code = hash_password(verification_code)
        user.verification_expires_at = expires_at
        user.code_purpose = CodePurpose.password_reset

        await db.commit()
        background_tasks.add_task(
            send_password_reset_otp, user.username, user.email, verification_code
        )

        return {
            "message": "If an account with that email exists,a password reset email has been sent."
        }

    async def reset_password(
        self, email: str, otp: str, new_password: str, db: AsyncSession
    ):

        user = await db.scalar(select(User).where(User.email == email))
        if not user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid credentials"
            )
        if user.verification_expires_at is None or not user.code_purpose == CodePurpose.password_reset:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code",
            )
        if user.verification_expires_at < datetime.now(UTC) or not verify_password(
            otp, user.verification_code
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid or expired verification code",
            )

        user.password_hash = hash_password(new_password)
        user.refresh_token = None
        user.verification_code = None
        user.verification_expires_at = None
        user.code_purpose = None
        await db.commit()

        return {"message": "Password changed"}

    async def delete_account(self, password: str, db: AsyncSession, current_user: User):
        if current_user.is_deleted is True:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="User not found"
            )
        if not verify_password(password, current_user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, detail="Incorrect password"
            )
        if not current_user.is_verified:
            await db.delete(current_user)
            await db.commit()
            return {"message": "Account_deleted"}

        current_user.is_deleted = True
        current_user.deleted_at = datetime.now(UTC)
        current_user.refresh_token = None
        await db.commit()
        return {
            "message": "Your account has been deactivated and will be permanently deleted after 30 days.You can restore it anytime before then by logging in with your email and password"
        }

    @staticmethod
    async def cleanup_inactive_deleted_users(db: AsyncSession):
        now = datetime.now(UTC)
        cutoff = now - timedelta(days=30)

        unverified_accounts_deleted = await db.execute(
            delete(User).where(User.is_verified.is_(False), User.created_at < cutoff)
        )
        deactivated_accounts_deleted = await db.execute(
            delete(User).where(User.is_deleted.is_(True), User.deleted_at < cutoff)
        )

        await db.commit()

        return {
            "deactivated_accounts_deleted": deactivated_accounts_deleted.rowcount,
            "unverified_accounts_deleted": unverified_accounts_deleted.rowcount,
        }
