import httpx

from src.auth.service import AuthService
from src.db import AsyncSessionLocal
from src.media.service import MediaService
from src.services.tmdb.exceptions import TMDBServiceError


async def genre_sync_job():
    async with AsyncSessionLocal() as db:
        async with httpx.AsyncClient() as client:
            try:
                await MediaService.sync_genres(client, db)
            except TMDBServiceError:
                print("Genre sync failed: TMDB service didn't respond")
                return


async def cleanup_expired_job():
    async with AsyncSessionLocal() as db:
        await AuthService.cleanup_inactive_deleted_users(db)
        return
