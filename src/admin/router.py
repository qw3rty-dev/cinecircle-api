from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import AuthService
from src.common.schemas import MessageResponse
from src.core.rate_limiting import limiter
from src.db import get_db
from src.enums import SortOrder, SortUsers, SortVerificationRequests
from src.media.service import MediaService
from src.models import User
from src.security.jwt_handler import get_current_admin
from src.services.tmdb.exceptions import TMDBServiceError

from .schema import (
    CleanResponse,
    PaginatedUserResponse,
    StatsResponse,
    SyncGenreResponse,
)
from .service import AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


admin_service = AdminService()


@router.get(
    "/users", response_model=PaginatedUserResponse, status_code=status.HTTP_200_OK
)
@limiter.limit("120/minute")
@limiter.limit("10/second")
async def get_users(
    request: Request,
    search: str | None = Query(default=None),
    deactivated: bool | None = Query(default=None),
    verified: bool | None = Query(default=None),
    private: bool | None = Query(default=None),
    limit: int = Query(default=20),
    page: int = Query(default=1),
    sort_by: SortUsers = Query(default=SortUsers.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return await admin_service.get_users(
        search,
        deactivated,
        verified,
        private,
        limit,
        page,
        sort_by,
        sort_order,
        db,
    )
@router.get(
    "/show/verification-requests", status_code=status.HTTP_200_OK
)
@limiter.limit("120/minute")
@limiter.limit("10/second")
async def show_verification_requests(
    request: Request,
    search: str | None = Query(default=None),
    expired: bool | None = Query(default=None),
    private: bool | None = Query(default=None),
    limit: int = Query(default=20),
    page: int = Query(default=1),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    sort_by: SortVerificationRequests = Query(default=SortVerificationRequests.request_created_at),
    db: AsyncSession = Depends(get_db),
    # current_admin: User = Depends(get_current_admin),
):
    return await admin_service.show_verification_requests(search,expired,private,limit,page,sort_by,sort_order,db)
    

@router.post(
    "/verify/users/{user_id}", response_model=MessageResponse, status_code=status.HTTP_200_OK
)
@limiter.limit("30/minute")
@limiter.limit("3/second")
async def verify_users_manually(
    request: Request,
    user_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return await admin_service.verify_users_manually(user_id,db)

@router.get(
    "/cinecircle/stats", response_model=StatsResponse, status_code=status.HTTP_200_OK
)
@limiter.limit("30/minute")
@limiter.limit("3/second")
async def get_cinecircle_stats(
    request: Request, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)
):
    return await admin_service.get_cinecircle_stats(db)


@router.post(
    "/genres/sync", response_model=SyncGenreResponse, status_code=status.HTTP_200_OK
)
@limiter.limit("30/minute")
@limiter.limit("3/second")
async def genres_sync(
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    try:
        client = request.app.state.http_client
        return await MediaService.sync_genres(client, db)
    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )


@router.post(
    "/cleanup/users", response_model=CleanResponse, status_code=status.HTTP_200_OK
)
@limiter.limit("30/minute")
@limiter.limit("3/second")
async def cleanup_inactive_unverified_users(
    request: Request, db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)
):
    return await AuthService.cleanup_inactive_deleted_users(db)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
@limiter.limit("5/second")
async def delete_review(
    request: Request,
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return await admin_service.delete_review(review_id, db)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
@limiter.limit("60/minute")
@limiter.limit("5/second")
async def delete_comment(
    request: Request,
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return await admin_service.delete_comment(comment_id, db)
