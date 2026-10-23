import pytest
from conftest import auth_headers, create_test_user, login_user, verify_user


@pytest.mark.asyncio
async def test_add_to_watchlist_requires_authentication(client, mock_tmdb_media):
    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_to_watchlist_successfull(
    client, mock_tmdb_media, db_session
):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
        headers=headers,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_fetch_watchlist_successfull(
    client, mock_tmdb_media, db_session
):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
        headers=headers,
    )

    watchlist = await client.get("/v1/watchlist", headers=headers)
    assert watchlist.json()["results"][0]["id"] == response.json()["id"]


@pytest.mark.asyncio
async def test_remove_from_watchlist(client, mock_tmdb_media, db_session):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
        headers=headers,
    )
    assert response.status_code == 201
    media_id = response.json()["id"]

    delete = await client.request(
        "DELETE", f"/v1/watchlist/{media_id}", headers=headers
    )

    watchlist = await client.get("/v1/watchlist", headers=headers)
    assert delete.status_code == 204
    assert watchlist.json()["meta"]["total"] == 0
