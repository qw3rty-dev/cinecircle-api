import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import (
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.pool import NullPool

from src.db import get_db
from src.main import app
from src.models import User

TEST_DATABASE_URL = os.environ["TEST_DATABASE_URL"]

test_engine = create_async_engine(TEST_DATABASE_URL, poolclass=NullPool)


@pytest_asyncio.fixture
async def db_session():
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
async def override_db_dependency(db_session):
    async def _override_get_db():
        yield db_session

    return _override_get_db


@pytest_asyncio.fixture
async def client(override_db_dependency):
    app.dependency_overrides[get_db] = override_db_dependency
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
        app.dependency_overrides.pop(get_db, None)
        del app.state.http_client


@pytest_asyncio.fixture()
async def create_test_user(client):
    data = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "testuser",
        "is_private": False,
    }
    response = await client.post("/v1/auth/register", json=data)
    assert response.status_code == 201
    return response.json()


@pytest_asyncio.fixture()
async def auth_headers(client, create_test_user):
    login = await client.post(
        "/v1/auth/login",
        data={
            "username": create_test_user.get("email"),
            "password": "testuser",
        },
    )
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers


@pytest_asyncio.fixture()
async def auth_headers_verified(client, create_test_user, db_session):

    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    user.is_verified = True
    await db_session.commit()

    login = await client.post(
        "/v1/auth/login",
        data={
            "username": create_test_user.get("email"),
            "password": "testuser",
        },
    )
    access_token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {access_token}"}
    return headers


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

    with patch(
        "src.media.service.get_by_id",
        new_callable=AsyncMock,
        return_value=fake_media,
    ) as mocked:
        yield mocked
