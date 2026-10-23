import httpx
import redis.asyncio as redis
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from src.common.utils import get_media_info
from src.enums import MediaActivityType, MediaType, SearchMediaType
from src.models import Genre, Media, MediaActivity, MediaGenre, User
from src.services.tmdb.service import (
    get_by_id,
    get_genres,
    search_movie,
    search_tv,
    trending_movies,
    trending_tv,
)


async def add_genres_to_db(db: AsyncSession, genres: list[dict]):
    if not genres:
        return
    for genre in genres:
        new_genre = Genre(id=genre["id"], name=genre["name"])
        db.add(new_genre)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="genre already exists"
        )


async def fetch_existing_genres_id(db: AsyncSession):
    existing_genres = (await db.scalars(select(Genre))).all()
    results = set()
    for genre in existing_genres:
        results.add(genre.id)
    return results


async def get_genre_names(db: AsyncSession):
    genres = (await db.scalars(select(Genre))).all()
    results = {}
    for genre in genres:
        results[genre.id] = genre.name
    return results


async def add_activities(
    activity: MediaActivityType, media_id: int, current_user: User, db: AsyncSession
):
    if activity != MediaActivityType.watched:
        watched_activity = MediaActivity(
            media_id=media_id,
            user_id=current_user.id,
            activity=MediaActivityType.watched,
        )
        db.add(watched_activity)

    media_activity = MediaActivity(
        media_id=media_id, user_id=current_user.id, activity=activity
    )
    db.add(media_activity)
    await db.commit()
    return {"message": "Activity updated"}


async def get_or_fetch(
    db: AsyncSession,
    func,
    media_type: MediaType,
    client: httpx.AsyncClient,
    redis_client: redis.Redis,
    search: str | None = None,
    page: int = 1,
):
    results = []
    if search:
        tmdb_response = await func(client, redis_client, search, page)
    else:
        tmdb_response = await func(client, redis_client, page)
    search_results = {
        "query": search,
        "page": page,
        "total_pages": tmdb_response.get("total_pages") or 0,
        "total_results": tmdb_response.get("total_results") or 0,
    }

    media = tmdb_response.get("results")
    genres_info = await get_genre_names(db)
    for item in media:
        movie_info = get_media_info(item, media_type.value, genres_info)
        results.append(movie_info)
    search_results["results"] = results
    return search_results


class MediaService:
    async def search(
        self,
        search: str,
        media_type: SearchMediaType,
        page: int,
        client: httpx.AsyncClient,
        redis_client: redis.Redis,
        db: AsyncSession,
    ):

        if media_type == SearchMediaType.movie:
            search_results = await get_or_fetch(
                db, search_movie, SearchMediaType.movie, client, redis_client, search, page
            )

        if media_type == SearchMediaType.tv:
            search_results = await get_or_fetch(
                db, search_tv, SearchMediaType.tv, client, redis_client, search, page
            )

        if media_type == SearchMediaType.all:
            movie = await get_or_fetch(
                db, search_movie, SearchMediaType.movie, client, redis_client, search, page
            )
            tv = await get_or_fetch(
                db, search_tv, SearchMediaType.tv, client, redis_client, search, page
            )
            search_results = {
                "query": search,
                "page": page,
                "total_pages": max(movie.get("total_pages"), tv.get("total_pages")),
                "total_results": movie.get("total_results") + tv.get("total_results"),
                "results": movie.get("results") + tv.get("results"),
            }

        return search_results

    async def trending_movies(
        self, page: int, client: httpx.AsyncClient, redis_client: redis.Redis, db: AsyncSession
    ):

        results = await get_or_fetch(
            db=db,
            func=trending_movies,
            media_type=MediaType.movie,
            client=client,
            redis_client=redis_client,
            page=page,
        )
        return results

    async def trending_tv(self, page: int, client: httpx.AsyncClient, redis_client: redis.Redis, db: AsyncSession):

        results = await get_or_fetch(
            db=db,
            func=trending_tv,
            media_type=MediaType.tv,
            client=client,
            redis_client=redis_client,
            page=page,
        )
        return results
    
    async def get_by_id(
        self,
        tmdb_id: int,
        media_type: MediaType,
        client: httpx.AsyncClient,
        redis_client:redis.Redis,
        db: AsyncSession,
    ):
        media = await get_by_id(client, redis_client, tmdb_id, media_type)
        genres_info = await get_genre_names(db)
        return get_media_info(media, media_type.value, genres_info)

    async def set_media_activity(
        self,
        tmdb_id: int,
        media_type: MediaType,
        activity: MediaActivityType,
        db: AsyncSession,
        current_user: User,
        client: httpx.AsyncClient,
    ):
        media_id = await MediaService.get_or_create_media(
            tmdb_id, media_type, db, client
        )
        existing_activities = (
            await db.scalars(
                select(MediaActivity).where(
                    MediaActivity.user_id == current_user.id,
                    MediaActivity.media_id == media_id,
                )
            )
        ).all()
        if not existing_activities:
            return await add_activities(activity, media_id, current_user, db)
        existing = {
            existing_activity.activity: existing_activity
            for existing_activity in existing_activities
        }

        if activity not in existing:
            for activity_type in existing:
                if activity_type != MediaActivityType.watched:
                    await db.delete(
                        existing[activity_type]
                    )  # removing loved,liked or disliked

            new_activity = MediaActivity(
                media_id=media_id, user_id=current_user.id, activity=activity
            )
            db.add(new_activity)  # adding loved,liked or disliked
            await db.commit()
            return {"message": "Activity updated"}

        if activity == MediaActivityType.watched:
            for existing_activity in existing_activities:
                await db.delete(existing_activity)
            await db.commit()
            return {"message": "Activity updated"}

        if activity in existing:
            await db.delete(existing[activity])
            await db.commit()
            return {"message": "Activity updated"}

    @staticmethod
    async def get_or_create_media(
        tmdb_id: int, media_type: MediaType, db: AsyncSession, client: httpx.AsyncClient, redis_client: redis.Redis
    ):
        existing_media = await db.scalar(
            select(Media).where(
                Media.tmdb_id == tmdb_id, Media.media_type == media_type
            )
        )
        if existing_media:
            return existing_media.id

        media = await get_by_id(client, redis_client, tmdb_id, media_type)
        genres_info = await get_genre_names(db)
        data = get_media_info(media, media_type.value, genres_info)
        new_media = Media(
            tmdb_id=tmdb_id,
            media_type=media_type,
            title=data.get("title") or data.get("name"),
            premiere_date=data.get("release_date") or data.get("first_air_date"),
            poster_path=data.get("poster_path"),
        )
        db.add(new_media)
        await db.flush()

        for genre in data.get("genres"):
            genre_media_object = MediaGenre(media_id=new_media.id, genre_id=genre["id"])
            db.add(genre_media_object)

        try:
            await db.commit()
            await db.refresh(new_media)

        except IntegrityError:
            await db.rollback()
            existing_media = await db.scalar(
                select(Media).where(
                    Media.tmdb_id == tmdb_id, Media.media_type == media_type
                )
            )
            return existing_media.id

        return new_media.id

    @staticmethod
    async def sync_genres(client: httpx.AsyncClient, db: AsyncSession):

        existing_genres_id = await fetch_existing_genres_id(db)
        external_genres = await get_genres(client)
        new_genres = [
            genre for genre in external_genres if genre["id"] not in existing_genres_id
        ]
        await add_genres_to_db(db, new_genres)
        return {"added": len(new_genres)}
