import asyncio
import os

import httpx
import redis.asyncio as redis
from dotenv import load_dotenv

from src.enums import MediaType
from src.services.redis_service.cache_media import get_cache, set_cache

from .exceptions import TMDBServiceError

load_dotenv()
ACCESS_TOKEN = os.getenv("ACCESS_TOKEN")

RETRY_STATUS_CODES = {429, 500, 502, 503, 504}
MAX_RETRIES = 3


async def request_data(client: httpx.AsyncClient, url:str , params: dict | None = None):
    headers = {
        "User-Agent": "CineSearch/1.0 (+https://example.com)",
        "accept": "application/json",
        "Authorization": ACCESS_TOKEN,
    }
    print("Calling TMDB....\n")
    for attempt in range(1, MAX_RETRIES + 1):
        print(attempt)
        delay = 2**attempt
        try:
            req = await client.get(url=url, params=params, headers=headers)
            if req.status_code in RETRY_STATUS_CODES:
                if req.status_code == 429:
                    retry_after = req.headers.get("Retry-After")
                    if retry_after is not None:
                        try:
                            delay = int(retry_after)
                        except ValueError:
                            pass
                if attempt == MAX_RETRIES:
                    req.raise_for_status()
                await asyncio.sleep(delay)
                continue
            req.raise_for_status()
            return req.json()
        except httpx.ConnectError as e:
            print("Could not connect to TMDB.  ")
            if attempt == MAX_RETRIES:
                raise TMDBServiceError("Could not connect to TMDB.") from e
            await asyncio.sleep(2**attempt)

        except httpx.TimeoutException as e:
            print("TMDB took too long to respond.")
            if attempt == MAX_RETRIES:
                raise TMDBServiceError("TMDB took too long to respond.") from e
            await asyncio.sleep(2**attempt)

        except httpx.HTTPStatusError as e:
            print(f"TMDB returned an HTTP error: {e}")
            print(req.text)
            raise TMDBServiceError(f"TMDB returned an HTTP error:{e}") from e


async def get_genres(client: httpx.AsyncClient):
    results = []
    for media_type in ["tv", "movie"]:
        url = f"https://api.themoviedb.org/3/genre/{media_type}/list"
        data = await request_data(client, url)
        for item in data["genres"]:
            if item not in results:
                results.append(item)
    return results


async def get_recommendation(
    media_type: MediaType, tmdb_id: int, redis_client:redis, client: httpx.AsyncClient
):
    
    key = f"recommendation:{tmdb_id}:{media_type.value}"
    cached_result = await get_cache(key,redis_client)
    if cached_result is not None:
        return cached_result
    
    url = f"https://api.themoviedb.org/3/{media_type.value}/{tmdb_id}/recommendations?language=en-US&page=1"
    data = await request_data(client, url)
    await set_cache(key,86400,data,redis_client)

    return data


async def search_tv(client: httpx.AsyncClient, redis_client:redis, search: str, page: int = 1):

    search = search.lower().strip()
    key = f"search:{search}:tv:{page}"
    cached_result = await get_cache(key,redis_client)
    if cached_result is not None:
        return cached_result

    url = "https://api.themoviedb.org/3/search/tv"
    params = {"query": search, "page": page}

    data = await request_data(client, url, params)
    await set_cache(key,7200,data,redis_client)

    return data


async def search_movie(client: httpx.AsyncClient, redis_client:redis, search: str, page: int = 1):

    search = search.lower().strip()
    key = f"search:{search}:movie:{page}"
    cached_result = await get_cache(key,redis_client)
    if cached_result is not None:
        return cached_result

    url = "https://api.themoviedb.org/3/search/movie"
    params = {"query": search, "page": page}

    data = await request_data(client, url, params)
    await set_cache(key,7200,data,redis_client)

    return data


async def trending_movies(client: httpx.AsyncClient, redis_client:redis, page: int = 1):

    key = f"trending:movie:{page}"
    cached_result = await get_cache(key,redis_client)
    if cached_result is not None:
        return cached_result

    url = "https://api.themoviedb.org/3/trending/movie/day"
    params = {"page": page}
    data = await request_data(client, url, params)
    key = f"trending:movie:{page}"
    await set_cache(key,3600,data,redis_client)
    return data


async def trending_tv(client: httpx.AsyncClient, redis_client:redis, page: int = 1):

    key = f"trending:tv:{page}"
    cached_result = await get_cache(key,redis_client)
    if cached_result is not None:
        return cached_result

    url = "https://api.themoviedb.org/3/trending/tv/day"
    params = {"page": page}
    data = await request_data(client, url, params)
    key = f"trending:tv:{page}"
    await set_cache(key,3600,data,redis_client)
    return data


async def get_by_id(client: httpx.AsyncClient, redis_client:redis, tmdb_id: int, media_type: MediaType):

    key = f"{tmdb_id}:{media_type.value}"
    cached_result = await get_cache(key,redis_client)
    if cached_result is not None:
        return cached_result
    
    url = f"https://api.themoviedb.org/3/{media_type.value}/{tmdb_id}"
    data = await request_data(client, url)
    await set_cache(key,3600,data,redis_client)
    return data
