import pytest
from sqlalchemy import select

from src.models import Review


@pytest.mark.asyncio
async def test_add_review_requires_authentication(client, mock_tmdb_media):
    response = await client.post(
        "/v1/reviews",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
            "rating": 5,
            "content": "A great film.",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_review_invalid_rating_limit(
    client, mock_tmdb_media, auth_headers_verified
):
    response = await client.post(
        "/v1/reviews",
        json={
            "tmdb_id": 550,
            "media_type": "movie",
            "rating": 6,
            "content": "A great film.",
        },
        headers=auth_headers_verified,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_add_review_successful(
    client, mock_tmdb_media, auth_headers_verified, db_session
):

    json = {
        "tmdb_id": 550,
        "media_type": "movie",
        "rating": 5,
        "content": "A great film.",
    }
    response = await client.post(
        "/v1/reviews", json=json, headers=auth_headers_verified
    )
    assert response.status_code == 201
    review = await db_session.scalar(
        select(Review).where(Review.id == response.json()["id"])
    )
    assert review.content == json["content"]
    assert review.rating == json["rating"]


@pytest.mark.asyncio
async def test_add_review_same_media_twice(
    client, mock_tmdb_media, auth_headers_verified, db_session
):

    json = {
        "tmdb_id": 550,
        "media_type": "movie",
        "rating": 5,
        "content": "A great film.",
    }
    first_response = await client.post(
        "/v1/reviews", json=json, headers=auth_headers_verified
    )

    assert first_response.status_code == 201
    second_response = await client.post(
        "/v1/reviews", json=json, headers=auth_headers_verified
    )
    assert second_response.status_code == 409


@pytest.mark.asyncio
async def test_get_reviews_for_media(client, mock_tmdb_media, auth_headers_verified):

    json = {
        "tmdb_id": 550,
        "media_type": "movie",
        "rating": 5,
        "content": "A great film.",
    }
    review = await client.post("/v1/reviews", json=json, headers=auth_headers_verified)

    media_id = review.json()["media"]["id"]
    response = await client.get(
        f"/v1/reviews/media/{media_id}", headers=auth_headers_verified
    )
    assert response.status_code == 200
