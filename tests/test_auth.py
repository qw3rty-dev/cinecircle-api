from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.models import User
from src.security.password import hash_password, verify_password


@pytest.mark.asyncio
async def test_register_successful(client):

    response = await client.post(
        "/v1/auth/register",
        json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "password",
            "is_private": True,
        },
    )
    assert response.status_code == 201


@pytest.mark.asyncio
async def test_register_existing_email(client, create_test_user):

    response = await client.post(
        "/v1/auth/register",
        json={
            "username": "new_user",
            "email": "test@example.com",  ##create test user already creates a user with this email
            "password": "password",
            "is_private": True,
        },
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_register_invalid_input(client):

    response = await client.post(
        "/v1/auth/register",
        json={
            "username": "new_user",
            "email": "test@example.com",
            "password": "123456",  # password should be of length greater than or equal to 8
            "is_private": True,
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_check_plaintext_password(client, db_session):

    json = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "password",
        "is_private": True,
    }
    response = await client.post("/v1/auth/register", json=json)
    assert response.status_code == 201
    user = await db_session.scalar(
        select(User).where(User.username == json["username"])
    )
    assert user.password_hash != json["password"]


@pytest.mark.asyncio
async def test_register_check_user_verification_status(client, db_session):

    json = {
        "username": "test_user",
        "email": "test@example.com",
        "password": "password",
        "is_private": True,
    }
    await client.post("/v1/auth/register", json=json)
    user = await db_session.scalar(
        select(User).where(User.username == json["username"])
    )
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_login(client, create_test_user):
    response = await client.post(
        "/v1/auth/login",
        data={
            "username": create_test_user.get("email"),
            "password": "testuser",
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client, create_test_user):

    response = await client.post(
        "/v1/auth/login",
        data={
            "username": create_test_user.get("email"),
            "password": "wrong_password",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):

    response = await client.post(
        "/v1/auth/login",
        data={
            "username": "non_existent_user@gmail.com",
            "password": "password",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_send_verification_email(client, auth_headers):
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    with (
        patch(
            "src.auth.service.verification_code_generate",
            return_value=("123456", expires_at),
        ),
        patch("src.auth.service.send_verification_mail") as mock_email,
    ):
        response = await client.post(
            "/v1/auth/verify_email",
            headers=auth_headers,
        )

    assert response.status_code == 200
    assert response.json()["message"] == "Verification code sent."
    mock_email.assert_called_once()
    mock_email.assert_called_once_with("test_user", "test@example.com", "123456")


@pytest.mark.asyncio
async def test_verify_email_confirm(client, create_test_user, db_session, auth_headers):
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    await db_session.commit()

    response = await client.post(
        "/v1/auth/verify_email/confirm", json={"otp": "123456"}, headers=auth_headers
    )
    assert response.status_code == 200
    assert response.json() == {"message": "Verification done."}
    await db_session.refresh(user)
    assert user.is_verified is True


@pytest.mark.asyncio
async def test_verify_email_confirm_wrong_otp(
    client, create_test_user, db_session, auth_headers
):
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    await db_session.commit()

    response = await client.post(
        "/v1/auth/verify_email/confirm", json={"otp": "000000"}, headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification code."}
    await db_session.refresh(user)
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_verify_email_confirm_expired_otp(
    client, create_test_user, db_session, auth_headers
):
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) - timedelta(
        minutes=10
    )  # intentionally set to 10 mins ago
    await db_session.commit()

    response = await client.post(
        "/v1/auth/verify_email/confirm", json={"otp": "123456"}, headers=auth_headers
    )
    assert response.status_code == 400
    assert response.json() == {"detail": "Invalid or expired verification code."}
    await db_session.refresh(user)
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_verify_email_invalid_input(
    client, create_test_user, db_session, auth_headers
):
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    await db_session.commit()

    response = await client.post(
        "/v1/auth/verify_email/confirm", json={}, headers=auth_headers
    )
    assert response.status_code == 422
    await db_session.refresh(user)
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_change_password_successfully(client, auth_headers):

    response = await client.patch(
        "/v1/auth/change_password",
        json={
            "current_password": "testuser",
            "new_password": "new_password",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_error(client, auth_headers):

    response = await client.patch(
        "/v1/auth/change_password",
        json={
            "current_password": "wrong_password",
            "new_password": "new_password",
        },
        headers=auth_headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_change_password_invalid_new_password(client, auth_headers):

    response = await client.patch(
        "/v1/auth/change_password",
        json={
            "current_password": "testuser",
            "new_password": "123456",
        },
        headers=auth_headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_change_password_updated_the_db(
    client, create_test_user, auth_headers, db_session
):

    json = {
        "current_password": "testuser",
        "new_password": "new_password",
    }
    await client.patch("/v1/auth/change_password", json=json, headers=auth_headers)
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    assert verify_password(json["new_password"], user.password_hash) is True
    assert verify_password(json["current_password"], user.password_hash) is False


@pytest.mark.asyncio
async def test_delete_account_successfully(client, auth_headers):

    response = await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "testuser",
        },
        headers=auth_headers,
    )
    assert response.status_code == 200
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_delete_account_wrong_password(client, auth_headers):

    response = await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "wrong_password",
        },
        headers=auth_headers,
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_account_check_result_unverified_account(
    client, create_test_user, auth_headers, db_session
):

    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )

    assert user.is_verified is False

    await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "testuser",
        },
        headers=auth_headers,
    )
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )

    assert user is None


@pytest.mark.asyncio
async def test_delete_account_check_result_verified_account(
    client, create_test_user, auth_headers, db_session
):

    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    user.is_verified = True
    await db_session.commit()
    await db_session.refresh(user)
    assert user.is_verified is True
    assert user.is_deleted is False

    await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "testuser",
        },
        headers=auth_headers,
    )
    user = await db_session.scalar(
        select(User).where(User.email == create_test_user["email"])
    )
    assert user is not None
    assert user.is_deleted is True
