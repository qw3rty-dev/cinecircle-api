from math import ceil

import pytest
from sqlalchemy import select

from src.models import User
from src.enums import RelationshipStatus
from tests.conftest import auth_headers, create_test_user, login_user, verify_user


@pytest.mark.asyncio
async def test_follow_public_user_successful(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com",password="test_password")
    headers = auth_headers(token)

    # second public verified account following first public unverified account
    first_user_id = first_create_user_response['id']
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["message"] == "Following"
    assert follow_response.status_code == 201


@pytest.mark.asyncio
async def test_follow_request_private_user_successful(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password",is_private=True)
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com",password="test_password")
    headers = auth_headers(token)

    # second public verified account following first private unverified account
    first_user_id = first_create_user_response['id']
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["message"] == "Follow request sent"
    assert follow_response.status_code == 201


@pytest.mark.asyncio
async def test_follow_requires_verification(client):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    token = await login_user(client,email="test2@example.com",password="test_password")
    headers = auth_headers(token)

    # second public unverified account following first public unverified account
    first_user_id = first_create_user_response['id']
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["detail"] == "Please verify your email to use this feature."
    assert follow_response.status_code == 403


@pytest.mark.asyncio
async def test_follow_users_following_themselves(client, db_session):

    create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com",password="test_password")
    headers = auth_headers(token)

    # userA trying to follow userA
    user_id = create_user_response['id']
    follow_response = await client.post(f"v1/users/{user_id}/follow",headers=headers)
    assert follow_response.json()["detail"] == "You cannot follow yourself"
    assert follow_response.status_code == 400

@pytest.mark.asyncio
async def test_following_same_public_user_twice_returns_conflict(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com",password="test_password")
    headers = auth_headers(token)

    # second public verified account following first public unverified account 
    first_user_id = first_create_user_response['id']
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["message"] == "Following"
    assert follow_response.status_code == 201

    # second public verified account following first public unverified account again
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["detail"] == "Already following"
    assert follow_response.status_code == 409

@pytest.mark.asyncio
async def test_follow_request_to_same_user_twice_returns_conflict(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password",is_private=True)
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com",password="test_password")
    headers = auth_headers(token)

    # second public verified account following first private unverified account
    first_user_id = first_create_user_response['id']
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["message"] == "Follow request sent"
    assert follow_response.status_code == 201

    # second public verified account following first private unverified account again
    follow_response = await client.post(f"v1/users/{first_user_id}/follow",headers=headers)
    assert follow_response.json()["detail"] == "Request already sent"
    assert follow_response.status_code == 409

@pytest.mark.asyncio
async def test_follow_user_requires_authentication(client):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")

    # unauthenticated user trying to follow first_test_user
    first_user_id = first_create_user_response['id']
    follow_response = await client.post(f"v1/users/{first_user_id}/follow")
    assert follow_response.json()["detail"] == "Not authenticated"
    assert follow_response.status_code == 401

@pytest.mark.asyncio
async def test_follow_user_nonexistent_user(client, db_session):

    create_user_response = await create_test_user(client)
    await verify_user(create_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    # public verified user trying to follow a user with id 99999 which doesn't exist in db
    follow_response = await client.post("v1/users/99999/follow",headers=headers)
    assert follow_response.json()["detail"] == "User not found"
    assert follow_response.status_code == 404


@pytest.mark.asyncio
async def test_search_user(client):

    names = ["aakash","brightbill","fleabag","flickverse","priyanshu","rishabh","ruri","taylor"]
    suffixes = ["_12","123"]
    for name in names:
        for i,suffix in enumerate(suffixes,1):
             await create_test_user(client,username=f"{name}{suffix}",email=f"{name}{i}@example.com",password="test_password")

    search_response = await client.get("v1/users/search?search=a") # no authentication required
    assert search_response.status_code ==200

@pytest.mark.asyncio
async def test_search_user_pagination(client):

    names = ["aakash","ava","andrea","badal","baron"]
    suffixes = ["_12","123","_0_98","1_111","_","_x_x","_1.1","_dev","_pvt","_official"]
    for name in names:
        for i,suffix in enumerate(suffixes,1):
             await create_test_user(client,username=f"{name}{suffix}",email=f"{name}{i}@example.com",password="test_password")

    search_response = await client.get("v1/users/search?search=aa")
    assert search_response.status_code == 200
    assert search_response.json()['meta']['total'] == 10
    assert search_response.json()['meta']['total_pages'] == ceil(search_response.json()['meta']['total']/search_response.json()['meta']['limit'])
    assert search_response.json()['meta']['has_next'] is False

    search_response = await client.get("v1/users/search?search=a&limit=10")
    assert search_response.status_code == 200
    assert search_response.json()['meta']['total'] == 30
    assert search_response.json()['meta']['total_pages'] == ceil(search_response.json()['meta']['total']/search_response.json()['meta']['limit'])
    assert search_response.json()['meta']['has_next'] is True

    search_response = await client.get("v1/users/search?search=ba&limit=5&page=2")
    assert search_response.status_code == 200
    assert search_response.json()['meta']['total'] == 20
    assert search_response.json()['meta']['total_pages'] == ceil(search_response.json()['meta']['total']/search_response.json()['meta']['limit'])
    assert search_response.json()['meta']['has_next'] is True
    assert search_response.json()['meta']['has_previous'] is True

    search_response = await client.get("v1/users/search?search=z&limit=5")
    assert search_response.status_code == 200
    assert search_response.json()['meta']['total'] == 0
    assert search_response.json()['meta']['total_pages'] == ceil(search_response.json()['meta']['total']/search_response.json()['meta']['limit'])
    assert search_response.json()['meta']['has_next'] is False

@pytest.mark.asyncio
async def test_show_follow_requests_verified_user(client,db_session):

    create_test_user_response = await create_test_user(client,is_private=True)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
    
    token = await login_user(client)
    headers = auth_headers(token)
    await verify_user(test_user_id,db_session)
    response = await client.get("v1/users/follow-requests",headers=headers)

    assert response.status_code == 200
    assert response.json()['meta']['total'] == 3
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    returned_names ={follower['username'] for follower in response.json()['results']}
    assert returned_names == set(names)


@pytest.mark.asyncio
async def test_show_follow_requests_unverified_user(client,db_session):

    create_test_user_response = await create_test_user(client,is_private=True)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
    
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get("v1/users/follow-requests",headers=headers)

    assert response.status_code == 200
    assert response.json()['meta']['total'] == 3
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    returned_names ={follower['username'] for follower in response.json()['results']}
    assert returned_names == set(names)

@pytest.mark.asyncio
async def test_view_outgoing_follow_requests_verified_user(client,db_session):

    names = ["aakash","badal","barbossa"]
    user_ids = []
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password",is_private=True)
        user_ids.append(create_user_response['id'])

    create_test_user_response = await create_test_user(client)
    test_user_id = create_test_user_response['id']
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    for user_id in user_ids:
        await client.post(f"v1/users/{user_id}/follow",headers=headers)
    

    response = await client.get("v1/users/me/follow-requests/sent",headers=headers)
    assert response.status_code == 200
    assert response.json()['meta']['total'] == 3
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    returned_names ={user['username'] for user in response.json()['results']}
    assert returned_names == set(names)



@pytest.mark.asyncio
async def test_show_my_followers_verified_user(client,db_session):

    create_test_user_response = await create_test_user(client)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
    
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert response.status_code == 200
    assert response.json()['meta']['total'] == 3
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    returned_names ={follower['username'] for follower in response.json()['results']}
    assert returned_names == set(names)


@pytest.mark.asyncio
async def test_show_my_followers_unverified_user(client,db_session):

    create_test_user_response = await create_test_user(client)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
    
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert response.status_code == 200
    assert response.json()['meta']['total'] == 3
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    returned_names ={follower['username'] for follower in response.json()['results']}
    assert returned_names == set(names)


@pytest.mark.asyncio
async def test_show_others_followers_verified_user(client,db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(second_create_user_response['id'],db_session)


    token = await login_user(client, email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}/followers",headers=headers)

    assert response.status_code == 200
    assert response.json()['meta']['total'] == 0
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False


@pytest.mark.asyncio
async def test_show_others_followers_unverified_user(client):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")


    token = await login_user(client, email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}/followers",headers=headers)

    assert response.status_code == 403
    assert response.json()['detail'] == "Please verify your email to use this feature."


@pytest.mark.asyncio
async def test_show_my_following_verified_user(client,db_session):

    create_test_user_response = await create_test_user(client)
    await verify_user(create_test_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{create_test_user_response['id']}/following",headers=headers)

    assert response.status_code == 200
    assert response.json()['meta']['total'] == 0
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    

@pytest.mark.asyncio
async def test_show_my_following_unverified_user(client):

    create_test_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{create_test_user_response['id']}/following",headers=headers)

    assert response.status_code == 200
    assert response.json()['meta']['total'] == 0
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    

@pytest.mark.asyncio
async def test_show_others_following_verified_user(client,db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
    await verify_user(second_create_user_response['id'],db_session)


    token = await login_user(client, email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}/following",headers=headers)

    assert response.status_code == 200
    assert response.json()['meta']['total'] == 0
    assert response.json()['meta']['total_pages'] == ceil(response.json()['meta']['total']/response.json()['meta']['limit'])
    assert response.json()['meta']['has_next'] is False
    
    
@pytest.mark.asyncio
async def test_show_others_following_unverified_user(client):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")


    token = await login_user(client, email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}/following",headers=headers)

    assert response.status_code == 403
    assert response.json()['detail'] == "Please verify your email to use this feature."


@pytest.mark.asyncio
async def test_show_my_profile_verified_user(client, db_session):

    create_test_user_response = await create_test_user(client)
    await verify_user(create_test_user_response['id'],db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{create_test_user_response['id']}",headers=headers)

    assert response.status_code == 200
    assert response.json()['username'] == create_test_user_response['username']
    assert response.json()['username'] == create_test_user_response['username']
    assert response.json()['can_view_content'] is True
    assert response.json()['relationship_status'] == RelationshipStatus.self


@pytest.mark.asyncio
async def test_show_my_profile_unverified_user(client):

    create_test_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{create_test_user_response['id']}",headers=headers)

    assert response.status_code == 200
    assert response.json()['username'] == create_test_user_response['username']
    assert response.json()['can_view_content'] is True
    assert response.json()['relationship_status'] == RelationshipStatus.self


@pytest.mark.asyncio
async def test_show_public_profile_verified_user(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
   
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}",headers=headers)

    assert response.status_code == 200
    assert response.json()['username'] == first_create_user_response['username']
    assert response.json()['can_view_content'] is True
    assert response.json()['relationship_status'] is None


@pytest.mark.asyncio
async def test_show_public_profile_unverified_user(client):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
   
    token = await login_user(client,email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}",headers=headers)

    assert response.status_code == 403
    assert response.json()['detail'] == "Please verify your email to use this feature."


@pytest.mark.asyncio
async def test_show_private_profile_verified_user(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password",is_private=True)
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
   
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}",headers=headers)

    assert response.status_code == 200
    assert response.json()['username'] == first_create_user_response['username']
    assert response.json()['can_view_content'] is False
    assert response.json()['relationship_status'] is None


@pytest.mark.asyncio
async def test_show_private_profile_unverified_user(client):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password",is_private=True)
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
   
    token = await login_user(client,email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    response = await client.get(f"v1/users/{first_create_user_response['id']}",headers=headers)

    assert response.status_code == 403
    assert response.json()['detail'] == "Please verify your email to use this feature."


@pytest.mark.asyncio
async def test_view_profile_user_follows(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password")
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
   
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    follow_response = await client.post(f"v1/users/{first_create_user_response['id']}/follow",headers=headers)
    assert follow_response.status_code == 201
    response = await client.get(f"v1/users/{first_create_user_response['id']}",headers=headers)

    assert response.status_code == 200
    assert response.json()['username'] == first_create_user_response['username']
    assert response.json()['can_view_content'] is True
    assert response.json()['relationship_status'] == RelationshipStatus.following


@pytest.mark.asyncio
async def test_view_profile_user_pending_request(client, db_session):

    first_create_user_response = await create_test_user(client,username="first_test_user",email="test1@example.com",password="test_password",is_private=True)
    second_create_user_response = await create_test_user(client,username="second_test_user",email="test2@example.com",password="test_password")
   
    await verify_user(second_create_user_response['id'],db_session)
    token = await login_user(client,email="test2@example.com", password="test_password")
    headers = auth_headers(token)
    follow_response = await client.post(f"v1/users/{first_create_user_response['id']}/follow",headers=headers)
    assert follow_response.status_code == 201
    response = await client.get(f"v1/users/{first_create_user_response['id']}",headers=headers)

    assert response.status_code == 200
    assert response.json()['username'] == first_create_user_response['username']
    assert response.json()['can_view_content'] is False
    assert response.json()['relationship_status'] == RelationshipStatus.follow_request_sent


@pytest.mark.asyncio
async def test_accepting_follow_request_bulk(client,db_session):

    create_test_user_response = await create_test_user(client,is_private=True)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
        
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 3

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 0

    accept_response= await client.patch(
        "v1/users/follow-requests/bulk/accept_all",headers = headers
    )
    assert accept_response.status_code == 200
    assert accept_response.json()['message'] == "Requests accepted"

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 0

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 3


@pytest.mark.asyncio
async def test_rejecting_follow_request_bulk(client,db_session):

    create_test_user_response = await create_test_user(client,is_private=True)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
        
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 3

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 0

    accept_response= await client.patch(
        "v1/users/follow-requests/bulk/reject_all",headers = headers
    )
    assert accept_response.status_code == 200
    assert accept_response.json()['message'] == "Requests rejected"

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 0

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 0

@pytest.mark.asyncio
async def test_accept_follow_request_by_id(client,db_session):

    create_test_user_response = await create_test_user(client,is_private=True)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
        
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 3

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 0

    user_request_id = [request['request_id'] for request in follow_requests_response.json()['results'] if request['username'] == "badal"][0]
    accept_response= await client.patch(
        f"v1/users/follow-requests/{user_request_id}/accept",headers = headers
    )
    assert accept_response.status_code == 200
    assert accept_response.json()['message'] == "Request accepted"

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 2

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 1


@pytest.mark.asyncio
async def test_reject_follow_request_by_id(client,db_session):

    create_test_user_response = await create_test_user(client,is_private=True)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
        
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 3

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 0

    user_request_id = [request['request_id'] for request in follow_requests_response.json()['results'] if request['username'] == "badal"][0]
    accept_response= await client.patch(
        f"v1/users/follow-requests/{user_request_id}/reject",headers = headers
    )
    assert accept_response.status_code == 200
    assert accept_response.json()['message'] == "Request rejected"

    follow_requests_response = await client.get("v1/users/follow-requests",headers=headers)
    assert follow_requests_response.status_code == 200
    assert follow_requests_response.json()['meta']['total'] == 2

    followers_response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert followers_response.status_code == 200
    assert followers_response.json()['meta']['total'] == 0


@pytest.mark.asyncio
async def test_change_privacy_preference(client, db_session):
    create_user_response = await create_test_user(client,is_private=False)
    token = await login_user(client)
    headers = auth_headers(token)

    assert create_user_response['is_private'] is False
    response = await client.patch("v1/users/me/privacy",json={"is_private":True},headers=headers)

    assert response.status_code == 200
    assert response.json()["is_private"] is True
    user = await db_session.scalar(select(User).where(User.id == create_user_response['id']))
    assert user.is_private is True


@pytest.mark.asyncio
async def test_unfollow_user_by_user_id(client,db_session):

    names = ["aakash","badal","barbossa"]
    users = {}
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        users[create_user_response['username']] = create_user_response['id']

    create_test_user_response = await create_test_user(client)
    test_user_id = create_test_user_response['id']
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    for user in users:
        await client.post(f"v1/users/{users[user]}/follow",headers=headers)

    show_follow_response = await client.get(f"v1/users/{create_test_user_response['id']}/following",headers=headers)

    assert show_follow_response.status_code == 200
    assert show_follow_response.json()['meta']['total'] == 3

    delete_follow_response = await client.request("DELETE",f"v1/users/{users['aakash']}/follow",headers=headers)
    assert delete_follow_response.status_code == 204

    show_follow_response = await client.get(f"v1/users/{create_test_user_response['id']}/following",headers=headers)
    assert show_follow_response.status_code == 200
    assert show_follow_response.json()['meta']['total'] == 2

@pytest.mark.asyncio
async def test_unsend_follow_request_by_user_id(client,db_session):

    names = ["aakash","badal","barbossa"]
    users = {}
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password", is_private = True)
        users[create_user_response['username']] = create_user_response['id']

    create_test_user_response = await create_test_user(client)
    test_user_id = create_test_user_response['id']
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)
    for user in users:
        await client.post(f"v1/users/{users[user]}/follow",headers=headers)

    show_follow_request_response = await client.get("v1/users/me/follow-requests/sent",headers=headers)
    assert show_follow_request_response.status_code == 200
    assert show_follow_request_response.json()['meta']['total'] == 3

    delete_follow_response = await client.request("DELETE",f"v1/users/{users['aakash']}/follow",headers=headers)
    assert delete_follow_response.status_code == 204

    show_follow_request_response = await client.get("v1/users/me/follow-requests/sent",headers=headers)
    assert show_follow_request_response.status_code == 200
    assert show_follow_request_response.json()['meta']['total'] == 2

@pytest.mark.asyncio
async def test_remove_follower_by_user_id(client,db_session):

    create_test_user_response = await create_test_user(client)
    test_user_id = create_test_user_response['id']
    names = ["aakash","badal","barbossa"]
    users = {}
    for name in names:
        create_user_response = await create_test_user(client,username=f"{name}",email=f"{name}@example.com",password="test_password")
        users[create_user_response['username']] = create_user_response['id']
        await verify_user(create_user_response['id'],db_session)
        token = await login_user(client,email=f"{name}@example.com",password="test_password")
        headers = auth_headers(token)
        await client.post(f"v1/users/{test_user_id}/follow",headers=headers)
    
    await verify_user(test_user_id,db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert response.status_code == 200
    assert response.json()['meta']['total'] == 3

    remove_follower_response = await client.request("DELETE",f"v1/users/me/{users['aakash']}/follow",headers=headers)
    assert remove_follower_response.status_code == 204

    response = await client.get(f"v1/users/{test_user_id}/followers",headers=headers)
    assert response.status_code == 200
    assert response.json()['meta']['total'] == 2
    returned_names ={follower['username'] for follower in response.json()['results']}
    assert "aakash" not in returned_names
    
