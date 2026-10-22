from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.schemas import MessageResponse
from src.db import get_db
from src.enums import Action, BulkAction, SortOrder, SortUsers
from src.models import User
from src.security.jwt_handler import get_current_user, get_current_verified_user

from .schemas import (
    PaginatedFollowRequestResponse,
    PaginatedUserResponse,
    PrivacyPreference,
    UserProfile,
)
from .service import UserService

router = APIRouter(prefix="/users", tags=["connections"])

user_service = UserService()


@router.post(
    "/{user_id}/follow",
    response_model=MessageResponse,
    status_code=status.HTTP_201_CREATED,
)
async def follow_user(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await user_service.follow_user(user_id, db, current_user)


@router.get(
    "/search", response_model=PaginatedUserResponse, status_code=status.HTTP_200_OK
)
async def search_users(
    search: str,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sort_by: SortUsers = Query(default=SortUsers.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    db: AsyncSession = Depends(get_db),
):
    return await user_service.search_user(search, limit, page, sort_by, sort_order, db)


@router.get(
    "/follow-requests",
    response_model=PaginatedFollowRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def show_follow_requests(
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sort_by: SortUsers = Query(default=SortUsers.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.show_follow_requests_received(
        search, limit, page, sort_by, sort_order, db, current_user
    )
@router.get(
    "/me/follow-requests/sent",
    response_model=PaginatedFollowRequestResponse,
    status_code=status.HTTP_200_OK,
)
async def show_follow_requests_sent(
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sort_by: SortUsers = Query(default=SortUsers.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.show_follow_requests_sent(
        search, limit, page, sort_by, sort_order, db, current_user
    )


@router.get(
    "/{user_id}/followers",
    response_model=PaginatedUserResponse,
    status_code=status.HTTP_200_OK,
)
async def show_follower_list(
    user_id: int,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sort_by: SortUsers = Query(default=SortUsers.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.show_followers(
        user_id, search, limit, page, sort_by, sort_order, db, current_user
    )


@router.get(
    "/{user_id}/following",
    response_model=PaginatedUserResponse,
    status_code=status.HTTP_200_OK,
)
async def show_following_list(
    user_id: int,
    search: str | None = None,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    sort_by: SortUsers = Query(default=SortUsers.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.show_following(
        user_id, search, limit, page, sort_by, sort_order, db, current_user
    )


@router.get("/{user_id}", response_model=UserProfile, status_code=status.HTTP_200_OK)
async def show_user_profile(
    user_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):

    return await user_service.show_user_profile(user_id, current_user, db)


@router.patch(
    "/follow-requests/bulk/{action}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def request_action_bulk(
    action: BulkAction,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await user_service.request_action_bulk(action, db, current_user)


@router.patch(
    "/follow-requests/{request_id}/{action}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def request_action(
    request_id: int,
    action: Action,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await user_service.request_action(request_id, action, db, current_user)


@router.patch("/me/privacy", response_model=PrivacyPreference)
async def privacy_preferences(
    preference: PrivacyPreference,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return await user_service.privacy_preferences(
        preference.is_private, db, current_user
    )


@router.delete("/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def unfollow_user_or_unsend_request(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await user_service.unfollow_user_or_unsend_request(user_id, db, current_user)

@router.delete("/me/{user_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
async def remove_follower(
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    return await user_service.remove_follower_by_user_id(user_id, db, current_user)
