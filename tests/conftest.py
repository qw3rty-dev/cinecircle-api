import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.db import Base, get_db
from src.main import app
from src.models import User

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]



@pytest.fixture(scope="session")
def test_engine():
    engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)
    return engine

@pytest_asyncio.fixture(scope="session")
async def setup_db(test_engine):
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await test_engine.dispose()


@pytest_asyncio.fixture
async def db_session(test_engine,setup_db):
    async with test_engine.connect() as connection:
        transaction = await connection.begin()
        session_factory = async_sessionmaker(
            bind=connection,
            expire_on_commit=False,
            join_transaction_mode="create_savepoint",
        )

        async with session_factory() as session:
            try:
                yield session
            finally:
                await session.close()
                await transaction.rollback()


@pytest_asyncio.fixture
async def client(db_session):

    async def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    mock_http_client = MagicMock()
    mock_http_client.get = AsyncMock()
    app.state.http_client = mock_http_client

    try:
        async with AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
        ) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()
        del app.state.http_client


async def create_test_user(client:AsyncClient,
                           username:str="test_user",
                           email:str="test@example.com",
                           password:str="test_password",
                           is_private:bool=False):
    data = {
        "username": username,
        "email": email,
        "password": password,
        "is_private": is_private,
    }
    response = await client.post("/v1/auth/register", json=data)
    assert response.status_code == 201
    return response.json()


async def verify_user(user_id:int,
                      db_session:AsyncClient):
    user = await db_session.scalar(
        select(User).where(User.id == user_id)
    )
    user.is_verified = True
    await db_session.commit()


async def login_user(client:AsyncClient,
                     email:str="test@example.com",
                     password:str="test_password"):
    data = {
        "username": email,
        "password": password,
    }
    response = await client.post("/v1/auth/login", data=data)
    assert response.status_code == 200
    access_token = response.json()["access_token"]
    return access_token


def auth_headers(token):
    headers = {"Authorization": f"Bearer {token}"}
    return headers


async def create_comment(client:AsyncClient,
                           headers:str,
                           review_id:int,
                           content:str = "test_content"):
    
    response = await client.post(f"/v1/reviews/{review_id}/comments",json = {"content":content},headers=headers)
    return response

async def create_review(client:AsyncClient,
                        mock_tmdb_media,
                        headers:str,
                        rating:int,
                        content:str = "test_review"):
    
    json = {
        "tmdb_id": 550,
        "media_type": "movie",
        "rating": rating,
        "content": content,
    }
    response = await client.post("/v1/reviews",json = json,headers=headers)
    return response

# async def fake_media_factory(count:int):
#     ordinal_num = {1:"good", 2:"bad", 3:"excellent", 4:"mid", 5:"hulala"}
#     results = []
#     for i in range (1,count+1):
#         fake_media = {
#             "id": i+100,
#             "title": f"{i}_movie_{i}",
#             "release_date": f"199{i-1}-{i+2}-{i+10}",
#             "overview": f"{ordinal_num[i]}_movie_overview" if i<6 else f"{ordinal_num[10-i+1]}_movie_overview" ,
#             "poster_path": f"/example/{i*723}.jpg",
#             "genres": [],
#         }
#         results.append(fake_media)

#     return results

    
@pytest_asyncio.fixture
def mock_tmdb_media():
    fake_media = {
        "id": 550,
        "title": "Fight Club",
        "release_date": "1999-10-15",
        "overview": "An insomniac office worker...",
        "poster_path": "/example.jpg",
        "genres": [],
    }

    with(
         patch(
    "src.media.service.get_by_id",
        new_callable=AsyncMock,
        return_value=fake_media,
      ) as mock_media_service,
        patch(
        "src.reviews.service.get_by_id",
        new_callable=AsyncMock,
        return_value=fake_media,
      ) as mock_tmdb_service
    ):
        yield mock_media_service, mock_tmdb_service
