from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.db import get_db
from src.enums import SortOrder, SortWatchlist, WatchlistStatus
from src.models import User
from src.security.jwt_handler import get_current_verified_user
from src.services.tmdb.exceptions import TMDBServiceError

from .schemas import (
    AddToWatchlistRequest,
    PaginatedWatchlistResponse,
    UpdateWatchlistRequest,
    WatchlistResponse,
)
from .service import WatchListService

router = APIRouter(prefix="/watchlist", tags=["watchlist"])
watchlist_service = WatchListService()


@router.post("", response_model=WatchlistResponse, status_code=status.HTTP_201_CREATED)
async def add_to_watchlist(
    data: AddToWatchlistRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):
    try:
        client = request.app.state.http_client
        return await watchlist_service.add_to_watchlist(
            data.tmdb_id, data.media_type, db, current_user, client
        )

    except TMDBServiceError:
        raise HTTPException(status_code=503, detail="TMDB service didn't respond")


@router.get(
    "", response_model=PaginatedWatchlistResponse, status_code=status.HTTP_200_OK
)
async def fetch_watchlist(
    search: str | None = Query(default=None),
    status: WatchlistStatus | None = Query(default=None),
    sort_by: SortWatchlist = Query(default=SortWatchlist.created_at),
    sort_order: SortOrder = Query(default=SortOrder.desc),
    limit: int = Query(default=20, ge=1, le=100),
    page: int = Query(default=1, ge=1),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):

    return await watchlist_service.fetch_watchlist(
        search, status, sort_by, sort_order, limit, page, db, current_user
    )


@router.patch(
    "/{id}/status", response_model=WatchlistResponse, status_code=status.HTTP_200_OK
)
async def change_watching_status(
    id: int,
    update: UpdateWatchlistRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):

    return await watchlist_service.change_status(id, update.status, db, current_user)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_from_watchlist(
    id: int,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_verified_user),
):

    return await watchlist_service.remove_from_watchlist(id, db, current_user)
