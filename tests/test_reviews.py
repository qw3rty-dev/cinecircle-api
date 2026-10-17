from math import ceil

import pytest
from sqlalchemy import select

from src.models import Review
from tests.conftest import (
    auth_headers,
    create_comment,
    create_review,
    create_test_user,
    login_user,
    verify_user,
)


@pytest.mark.asyncio
async def test_add_review_successful(
    client, mock_tmdb_media, db_session
):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = 5,
                                   content= "test_review")
    
    assert response.status_code == 201
    review = await db_session.scalar(
        select(Review).where(Review.id == response.json()["id"])
    )
    assert review.content == "test_review"
    assert review.rating == 5


@pytest.mark.asyncio
async def test_add_review_same_media_twice(
    client, mock_tmdb_media, db_session
):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    first_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = 5,
                                   content= "test_review")
    
    assert first_response.status_code == 201

    second_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = 4,
                                   content= "another_test_review")
    assert second_response.status_code == 409
    
    assert second_response.json()["detail"] == "Review already exists"


@pytest.mark.asyncio
async def test_add_review_unverified_user(
    client, mock_tmdb_media, db_session
):
    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)
    
    response = await create_review(client,mock_tmdb_media, headers,5)
    assert response.status_code == 403
    assert response.json()["detail"] == "Please verify your email to use this feature."
\

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
async def test_add_review_invalid_media_rating_limit(
    client, mock_tmdb_media, db_session
):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    
    response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = 6,
                                   content= "test_review")
    assert response.status_code == 422



@pytest.mark.asyncio
async def test_get_reviews_for_media(client, mock_tmdb_media,db_session):

    ordinal_num = {1:"first", 2:"second", 3:"third", 4:"fourth", 5:"fifth"}

    for i in range(1,6):
        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers = auth_headers(token)

        review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = i,
                                   content= f"{ordinal_num[i]}_test_review")  
    

    response = await client.get(
        "/v1/reviews/media/550?media_type=movie"
    )
    # print(response.json())
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_reviews_for_media_pagination_test(client, mock_tmdb_media,db_session):

    
    ordinal_num = {1:"first", 2:"second", 3:"third", 4:"fourth", 5:"fifth"}
    for i in range(1,6):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers = auth_headers(token)
        review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = i,
                                   content= f"{ordinal_num[i]}_test_review")  
    

    response = await client.get(
        "/v1/reviews/media/550?media_type=movie&limit=2"
    )
    assert response.json()['meta']['total'] == 5
    assert response.json()['meta']['limit'] == 2
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is True
    assert response.status_code == 200

@pytest.mark.asyncio
async def test_get_reviews_for_media_not_saved_locally(client, mock_tmdb_media):

    response = await client.get(
        "/v1/reviews/media/550?media_type=movie&limit=2"
    )
    assert response.json()['meta']['limit'] == 2
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['total'] == 0 
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_add_comment_successful(client, mock_tmdb_media,db_session):

    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)

    review_response =await create_review(client,
                    mock_tmdb_media, 
                    headers = headers_by_id[1],
                    rating = 5,
                    content= "test_review")

    assert review_response.status_code == 201
    review_id = review_response.json()['id']

    comment_response = await create_comment(client,
                                            headers=headers_by_id[2],
                                            review_id=review_id,
                                            content= "test_comment")
    
    assert comment_response.status_code == 201
    assert comment_response.json()["content"] == "test_comment"


@pytest.mark.asyncio
async def test_add_multiple_comments(client, mock_tmdb_media,db_session):

    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    review_response = await create_review(client,
                                mock_tmdb_media, 
                                headers = headers_by_id[1],
                                rating = 5,
                                content= "test_review")  
    
    assert review_response.status_code == 201
    review_id = review_response.json()['id']

    first_comment_response = await create_comment(client,headers_by_id[2],review_id,"first_test_comment")
    second_comment_response = await create_comment(client,headers_by_id[2],review_id,"second_test_comment")
    third_comment_response = await create_comment(client,headers_by_id[1],review_id,"third_test_comment")

    assert first_comment_response.status_code == 201
    assert second_comment_response.status_code == 201
    assert third_comment_response.status_code == 201
    assert first_comment_response.json()["content"] == "first_test_comment"
    assert second_comment_response.json()["content"] == "second_test_comment"
    assert third_comment_response.json()["content"] == "third_test_comment"
    assert first_comment_response.json()["user"]["username"] == "second_test_user"
    assert second_comment_response.json()["user"]["username"] == "second_test_user"
    assert third_comment_response.json()["user"]["username"] ==  "first_test_user"


@pytest.mark.asyncio
async def test_add_comment_nonexistent_review(client, db_session):

    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    comment_response = await create_comment(client,headers,99999,"test_comment")
    
    assert comment_response.status_code == 404
    assert comment_response.json()["detail"] == "Review not found"


@pytest.mark.asyncio
async def test_add_comment_no_content(client, mock_tmdb_media, db_session):

    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = 5,
                                   content= "test_review")  
      
    comment_response = await create_comment(client,headers,review_response.json()['id'],"")
    assert comment_response.status_code == 422


@pytest.mark.asyncio
async def test_add_comment_requires_authentication(client, mock_tmdb_media, db_session):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers,
                                   rating = 5,
                                   content= "test_review")  

    comment_response = await create_comment(client=client,headers=None ,review_id=review_response.json()['id'],content="test_comment")

    assert comment_response.json()['detail'] == "Not authenticated"
    assert comment_response.status_code == 401


@pytest.mark.asyncio
async def test_add_comment_by_unverified_user(client, mock_tmdb_media, db_session):
    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    await verify_user(create_user_response['id'],db_session)
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers_by_id[2],
                                   rating = 5,
                                   content= "test_review")  
    comment_response = await create_comment(client=client,headers=headers_by_id[1] ,review_id=review_response.json()['id'],content="test_comment")

    assert comment_response.json()['detail'] == 'Please verify your email to use this feature.'
    assert comment_response.status_code == 403


@pytest.mark.asyncio
async def test_add_vote_user(client, mock_tmdb_media, db_session):
    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers_by_id[1],
                                   rating = 5,
                                   content= "test_review")  
    review_id = review_response.json()['id']
    vote_response = await client.put(f"/v1/reviews/{review_id}/vote?vote_type=upvote",headers = headers_by_id[2])
    print(vote_response.json())
    assert vote_response.status_code == 200
    assert vote_response.json()["vote_type"] == "upvote"

@pytest.mark.asyncio
async def test_add_vote_switch_another_votetype(client, mock_tmdb_media, db_session):
    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers_by_id[1],
                                   rating = 5,
                                   content= "test_review")  
    review_id = review_response.json()['id']
    vote_response = await client.put(f"/v1/reviews/{review_id}/vote?vote_type=upvote",headers = headers_by_id[2])
    assert vote_response.status_code == 200
    assert vote_response.json()["vote_type"] == "upvote"

    vote_response = await client.put(f"/v1/reviews/{review_id}/vote?vote_type=downvote",headers = headers_by_id[2])
    assert vote_response.status_code == 200
    assert vote_response.json()["vote_type"] == "downvote"


@pytest.mark.asyncio
async def test_add_vote_toogle(client, mock_tmdb_media, db_session):
    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers_by_id[1],
                                   rating = 5,
                                   content= "test_review")  
    review_id = review_response.json()['id']
    vote_response = await client.put(f"/v1/reviews/{review_id}/vote?vote_type=upvote",headers = headers_by_id[2])
    assert vote_response.status_code == 200
    assert vote_response.json()["vote_type"] == "upvote"

    vote_response = await client.put(f"/v1/reviews/{review_id}/vote?vote_type=upvote",headers = headers_by_id[2])
    assert vote_response.status_code == 200
    assert vote_response.json()["vote_type"] is None

@pytest.mark.asyncio
async def test_add_vote_nonexistent_review(client, db_session):

    create_user_response = await create_test_user(client,username="test_user",email="test@example.com",password="test_password")
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client,email="test@example.com",password="test_password")
    headers= auth_headers(token)

    vote_response = await client.put("/v1/reviews/999999/vote?vote_type=upvote",headers = headers)
    assert vote_response.status_code == 404
    assert vote_response.json()["detail"] == "Review not found"

    
@pytest.mark.asyncio
async def test_add_vote_requires_authentication(client):

    vote_response = await client.put("/v1/reviews/27/vote?vote_type=upvote")
    assert vote_response.status_code == 401
    assert vote_response.json()["detail"] == "Not authenticated"


@pytest.mark.asyncio
async def test_add_vote_unverified_user(client):

    create_user_response = await create_test_user(client,username="test_user",email="test@example.com",password="test_password")
    token = await login_user(client,email="test@example.com",password="test_password")
    headers= auth_headers(token)

    vote_response = await client.put("/v1/reviews/27/vote?vote_type=upvote",headers = headers)
    assert vote_response.status_code == 403
    assert vote_response.json()["detail"] == "Please verify your email to use this feature."

    
@pytest.mark.asyncio
async def test_add_vote_invalid_input(client, db_session):

    create_user_response = await create_test_user(client,username="test_user",email="test@example.com",password="test_password")
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client,email="test@example.com",password="test_password")
    headers= auth_headers(token)
    
    vote_response = await client.put("/v1/reviews/27/vote?vote_type=liked",headers = headers)
    #invalid vote_type (liked)
    assert vote_response.status_code == 422


@pytest.mark.asyncio
async def test_get_comments_successful(client, mock_tmdb_media, db_session):
    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers_by_id[1],
                                   rating = 5,
                                   content= "test_review")  
    review_id = review_response.json()['id']
    first_comment_response = await create_comment(client,headers_by_id[2],review_id,"first_test_comment")
    second_comment_response = await create_comment(client,headers_by_id[2],review_id,"second_test_comment")
    third_comment_response = await create_comment(client,headers_by_id[1],review_id,"third_test_comment")

    get_comments_response = await client.get(f"/v1/reviews/{review_id}/comments",headers = headers_by_id[2])

    assert get_comments_response.status_code == 200
    assert get_comments_response.json()['meta']['total'] == 3
    # print(get_comments_response.json())

@pytest.mark.asyncio
async def test_get_comments_pagination(client, mock_tmdb_media, db_session):
    headers_by_id = {}    
    ordinal_num = {1:"first", 2:"second"}
    for i in range(1,3):

        create_user_response = await create_test_user(client,username=f"{ordinal_num[i]}_test_user",email=f"test{i}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"test{i}@example.com",password="test_password")
        headers_by_id[i] = auth_headers(token)
    
    review_response = await create_review(client,
                                   mock_tmdb_media, 
                                   headers = headers_by_id[1],
                                   rating = 5,
                                   content= "test_review")  
    review_id = review_response.json()['id']
    for i in range(1,11):
        await create_comment(client,headers_by_id[2],review_id,f"{i}_test_comment_{i}")

    get_comments_response = await client.get(f"/v1/reviews/{review_id}/comments?limit=2",headers = headers_by_id[2])

    assert get_comments_response.json()['meta']['total'] == 10
    assert get_comments_response.json()['meta']['limit'] == 2
    assert get_comments_response.json()['meta']['total_pages'] == ceil(get_comments_response.json()['meta']['total']/get_comments_response.json()['meta']['limit'])
    assert get_comments_response.json()['meta']['has_next'] is True
    assert get_comments_response.status_code == 200


@pytest.mark.asyncio
async def test_get_comments_nonexistent_review(client, db_session):
    create_user_response = await create_test_user(client,username="test_user",email="test@example.com",password="test_password")
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client,email="test@example.com",password="test_password")
    headers= auth_headers(token)
    get_comments_response = await client.get("/v1/reviews/22222/comments",headers =headers)

    assert get_comments_response.status_code == 404
    assert get_comments_response.json()['detail'] == "Review not found"
