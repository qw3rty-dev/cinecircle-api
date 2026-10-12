import pytest


@pytest.mark.asyncio
async def test_add_to_watchlist_requires_authentication(client, mock_tmdb_media):
    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
    )
    print(response.json())
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_to_watchlist_successfull(
    client, mock_tmdb_media, auth_headers_verified
):
    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
        headers=auth_headers_verified,
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_fetch_watchlist_successfull(
    client, mock_tmdb_media, auth_headers_verified
):
    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
        headers=auth_headers_verified,
    )

    watchlist = await client.get("/v1/watchlist", headers=auth_headers_verified)
    assert watchlist.json()["results"][0]["id"] == response.json()["id"]


@pytest.mark.asyncio
async def test_remove_from_watchlist(client, mock_tmdb_media, auth_headers_verified):
    response = await client.post(
        "/v1/watchlist",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
        },
        headers=auth_headers_verified,
    )
    assert response.status_code == 201
    media_id = response.json()["id"]

    delete = await client.request(
        "DELETE", f"/v1/watchlist/{media_id}", headers=auth_headers_verified
    )

    watchlist = await client.get("/v1/watchlist", headers=auth_headers_verified)
    assert delete.status_code == 204
    assert watchlist.json()["meta"]["total"] == 0
