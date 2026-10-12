from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.schemas import MessageResponse
from src.db import get_db
from src.models import User
from src.security.jwt_handler import get_current_user

from .schemas import (
    ChangePassword,
    DeleteAccountRequest,
    ForgotPassword,
    RefreshRequest,
    ResetPassword,
    TokenResponse,
    UserCreate,
    UserResponse,
    VerifyOTP,
)
from .service import AuthService

router = APIRouter(prefix="/auth", tags=["authentication"])

auth_service = AuthService()


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
async def register(user: UserCreate, db: AsyncSession = Depends(get_db)):

    new_user = await auth_service.register(
        username=user.username,
        email=user.email,
        password=user.password,
        is_private=user.is_private,
        db=db,
    )
    return new_user


@router.post("/login", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def login(
    formdata: OAuth2PasswordRequestForm = Depends(), db: AsyncSession = Depends(get_db)
):

    token = await auth_service.login(
        email=formdata.username, password=formdata.password, db=db
    )
    return token


@router.post("/refresh", response_model=TokenResponse, status_code=status.HTTP_200_OK)
async def refresh(data: RefreshRequest, db: AsyncSession = Depends(get_db)):

    token_response = await auth_service.refresh(data.refresh_token, db=db)

    return token_response


@router.post("/logout", response_model=MessageResponse, status_code=status.HTTP_200_OK)
async def logout(
    current_user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)
):

    return await auth_service.logout(current_user, db)


@router.post(
    "/verify_email", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def send_verification_code(
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    return await auth_service.send_verification_code(background_tasks, current_user, db)


@router.post(
    "/verify_email/confirm",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def confirm_verification_code(
    verify: VerifyOTP,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    return await auth_service.confirm_verification_code(
        verification_otp=verify.otp, current_user=current_user, db=db
    )


@router.patch(
    "/change_password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def change_password(
    password: ChangePassword,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    return await auth_service.change_password(
        user=current_user,
        current_password=password.current_password,
        new_password=password.new_password,
        db=db,
    )


@router.post(
    "/forgot_password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def forgot_password(
    email: ForgotPassword,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):

    return await auth_service.forgot_password(
        email=email.email, background_tasks=background_tasks, db=db
    )


@router.post(
    "/reset_password", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def reset_password(reset: ResetPassword, db: AsyncSession = Depends(get_db)):

    return await auth_service.reset_password(
        email=reset.email, otp=reset.otp, new_password=reset.new_password, db=db
    )


@router.delete(
    "/delete-account", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
async def delete_account(
    data: DeleteAccountRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await auth_service.delete_account(data.password, db, current_user)
