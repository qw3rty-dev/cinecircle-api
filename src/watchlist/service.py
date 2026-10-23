import httpx
import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.common.utils import generate_meta
from src.enums import MediaType, SortOrder, SortWatchlist, WatchlistStatus
from src.media.service import MediaService
from src.models import Media, User, Watchlist


class WatchListService:
    async def add_to_watchlist(
        self,
        tmdb_id: int,
        media_type: MediaType,
        db: AsyncSession,
        current_user: User,
        client: httpx.AsyncClient,
        redis_client: redis.Redis
    ):

        media_id = await MediaService.get_or_create_media(
            tmdb_id, media_type, db, client, redis_client
        )
        watchlist_obj = Watchlist(media_id=media_id, user_id=current_user.id)

        try:
            db.add(watchlist_obj)
            await db.commit()
            watchlist_obj = await db.scalar(
                select(Watchlist)
                .options(selectinload(Watchlist.media))
                .where(Watchlist.id == watchlist_obj.id)
            )
        except IntegrityError:
            await db.rollback()
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Media already exists in watchlist",
            )
        return {
            "id": watchlist_obj.id,
            "media_id": watchlist_obj.media_id,
            "user_id": watchlist_obj.user_id,
            "status": watchlist_obj.status,
            "created_at": watchlist_obj.created_at,
            "media": watchlist_obj.media,
        }

    async def fetch_watchlist(
        self,
        search: str,
        status: WatchlistStatus,
        sort_by: SortWatchlist,
        sort_order: SortOrder,
        limit: int,
        page: int,
        db: AsyncSession,
        current_user: User,
    ):

        query = select(Watchlist).where(Watchlist.user_id == current_user.id)
        query = query.join(Watchlist.media).options(selectinload(Watchlist.media))
        if search:
            search = search.strip()
            query = query.where(Media.title.ilike(f"%{search}%"))
        if status:
            query = query.where(Watchlist.status == status.value)

        total = await db.scalar(select(func.count()).select_from(query.subquery()))
        sort_fields = {
            SortWatchlist.created_at: Watchlist.created_at,
            SortWatchlist.title: func.lower(Media.title),
        }
        sort_expression = sort_fields[sort_by]
        order = (
            sort_expression.asc()
            if sort_order == SortOrder.asc
            else sort_expression.desc()
        )
        query = query.order_by(order, Watchlist.id.desc())
        offset = (page - 1) * limit
        query = query.limit(limit).offset(offset)
        watchlist = (await db.scalars(query)).all()
        meta = generate_meta(page, limit, total)

        return {"meta": meta, "results": watchlist}

    async def change_status(
        self, id: int, new_status: str, db: AsyncSession, current_user: User
    ):
        watchlist_obj = await db.scalar(
            select(Watchlist)
            .options(selectinload(Watchlist.media))
            .where(Watchlist.id == id, Watchlist.user_id == current_user.id)
        )
        if not watchlist_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
            )
        if watchlist_obj.status != new_status:
            watchlist_obj.status = new_status
            await db.commit()

        return {
            "id": watchlist_obj.id,
            "media_id": watchlist_obj.media_id,
            "user_id": watchlist_obj.user_id,
            "status": watchlist_obj.status,
            "created_at": watchlist_obj.created_at,
            "media": watchlist_obj.media,
        }

    async def remove_from_watchlist(
        self, id: int, db: AsyncSession, current_user: User
    ):

        media = await db.scalar(
            select(Watchlist).where(
                Watchlist.id == id, Watchlist.user_id == current_user.id
            )
        )
        if not media:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Media not found"
            )

        await db.delete(media)
        await db.commit()
