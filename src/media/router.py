from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.schemas import MessageResponse
from src.db import get_db
from src.enums import MediaActivityType, MediaType, SearchMediaType
from src.models import User
from src.security.jwt_handler import get_current_user
from src.services.tmdb.exceptions import TMDBServiceError

from .schemas import (
    MovieResult,
    SearchAllResponse,
    SearchMovieResponse,
    SearchTvResponse,
    TrendingMovieResponse,
    TrendingTvResponse,
    TvResult,
)
from .service import MediaService

router = APIRouter(prefix="/media", tags=["media"])

media_service = MediaService()


@router.get(
    "/search/{search}",
    response_model=SearchMovieResponse | SearchTvResponse | SearchAllResponse,
    status_code=status.HTTP_200_OK,
)
async def search_media(
    request: Request,
    search: str,
    media_type: SearchMediaType = Query(default=SearchMediaType.all),
    page: int = Query(default=1),
    db: AsyncSession = Depends(get_db),
):
    try:
        client = request.app.state.http_client
        results = await media_service.search(search, media_type, page, client, db)
        return results

    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )


@router.get(
    "/trending/movie",
    response_model=TrendingMovieResponse,
    status_code=status.HTTP_200_OK,
)
async def trending_movies(
    request: Request, page: int = Query(default=1), db: AsyncSession = Depends(get_db)
):
    try:
        client = request.app.state.http_client
        results = await media_service.trending_movies(page, client, db)
        return results
    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )


@router.get(
    "/trending/tv", response_model=TrendingTvResponse, status_code=status.HTTP_200_OK
)
async def trending_tv(
    request: Request, page: int = Query(default=1), db: AsyncSession = Depends(get_db)
):
    try:
        client = request.app.state.http_client
        results = await media_service.trending_tv(page, client, db)
        return results
    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )


@router.get(
    "/{id}", response_model=MovieResult | TvResult, status_code=status.HTTP_200_OK
)
async def get_by_id(
    request: Request, id: int, media_type: MediaType, db: AsyncSession = Depends(get_db)
):
    try:
        client = request.app.state.http_client
        results = await media_service.get_by_id(id, media_type, client, db)
        return results
    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )


@router.post(
    "/{tmdb_id}/activity/{activity}",
    response_model=MessageResponse,
    status_code=status.HTTP_200_OK,
)
async def set_media_activity(
    request: Request,
    tmdb_id: int,
    media_type: MediaType,
    activity: MediaActivityType,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    try:
        client = request.app.state.http_client
        return await media_service.set_media_activity(
            tmdb_id, media_type, activity, db, current_user, client
        )
    except TMDBServiceError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="TMDB service didn't respond",
        )
