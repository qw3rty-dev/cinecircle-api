from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.service import AuthService
from src.db import get_db
from src.enums import SortOrder, SortUsers
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
async def get_users(
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
    "/cinecircle/stats", response_model=StatsResponse, status_code=status.HTTP_200_OK
)
async def get_cinecircle_stats(
    db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)
):
    return await admin_service.get_cinecircle_stats(db)


@router.post(
    "/genres/sync", response_model=SyncGenreResponse, status_code=status.HTTP_200_OK
)
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
async def cleanup_inactive_unverified_users(
    db: AsyncSession = Depends(get_db), current_admin: User = Depends(get_current_admin)
):
    return await AuthService.cleanup_inactive_deleted_users(db)


@router.delete("/reviews/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return await admin_service.delete_review(review_id, db)


@router.delete("/comments/{comment_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_comment(
    comment_id: int,
    db: AsyncSession = Depends(get_db),
    current_admin: User = Depends(get_current_admin),
):
    return await admin_service.delete_comment(comment_id, db)
