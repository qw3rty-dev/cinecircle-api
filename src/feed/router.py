from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.rate_limiting import limiter
from src.db import get_db
from src.enums import MediaType
from src.models import User
from src.security.jwt_handler import get_current_verified_user
from src.services.tmdb.exceptions import TMDBServiceError

from .schemas import PaginatedReviewResponse, RecommendationResponse
from .service import FeedService

router = APIRouter(prefix="/feed", tags=["feed"])


feed_services = FeedService()


@router.get("", response_model=RecommendationResponse, status_code=status.HTTP_200_OK)
@limiter.limit("30/minute")
@limiter.limit("3/second")
async def get_recommendations(
    request: Request,
    media_type: MediaType | None = Query(default=None),
    page: int = Query(default=1, ge=1, le=5),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):

    try:
        client = request.app.state.http_client
        redis_client = request.app.state.redis
        return await feed_services.get_recommendations(
            media_type, page, db, client, redis_client, current_user
        )
    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )


@router.get(
    "/following/activity",
    response_model=PaginatedReviewResponse,
    status_code=status.HTTP_200_OK,
)
@limiter.limit("30/minute")
@limiter.limit("3/second")
async def get_following_activity(
    request: Request,
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    current_user: User = Depends(get_current_verified_user),
    db: AsyncSession = Depends(get_db),
):
    return await feed_services.following_activity_reviews(limit, page, db, current_user)
