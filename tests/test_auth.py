from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from src.enums import CodePurpose
from src.models import User
from src.security.password import hash_password, verify_password
from tests.conftest import auth_headers, create_test_user, login_user, verify_user


@pytest.mark.asyncio
async def test_register_success(client, db_session):
    response = await client.post(
        "/v1/auth/register",
        json={
            "username": "test_user",
            "email": "test@example.com",
            "password": "test_password",
            "is_private": True,
        },
    )
    user = await db_session.scalar(select(User).where(User.id == response.json()["id"]))

    assert response.status_code == 201
    assert response.json()["username"] == "test_user"
    assert response.json()["email"] == "test@example.com"
    assert "password" not in response.json()
    assert "password_hash" not in response.json()
    assert user is not None


@pytest.mark.asyncio
async def test_register_validation_error(client):

    response = await client.post(
        "/v1/auth/register",
        json={
            "username": "test_user",
            "email": "test@example.com",
        },
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_register_duplicate_email(client):

    await create_test_user(client)
    response = await client.post(
        "/v1/auth/register",
        json={
            "username": "different_user",
            "email": "test@example.com",
            "password": "test_password2",
            "is_private": True,
        },
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "Email already exists"


@pytest.mark.asyncio
async def test_register_check_plaintext_password(client, db_session):

    create_user_response = await create_test_user(client)
    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    assert user.password_hash != "test_password"


@pytest.mark.asyncio
async def test_register_check_user_verification_status(client, db_session):

    create_user_response = await create_test_user(client)
    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_login_success(client):
    create_user_response = await create_test_user(client)
    response = await client.post(
        "/v1/auth/login",
        data={
            "username": create_user_response["email"],
            "password": "test_password",
        },
    )
    assert response.status_code == 200
    assert "access_token" in response.json()


@pytest.mark.asyncio
async def test_login_wrong_password(client):

    create_user_response = await create_test_user(client)
    response = await client.post(
        "/v1/auth/login",
        data={
            "username": create_user_response["email"],
            "password": "wrong_password",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_login_nonexistent_user(client):

    response = await client.post(
        "/v1/auth/login",
        data={
            "username": "non_existent_user@gmail.com",
            "password": "test_password",
        },
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid credentials"


@pytest.mark.asyncio
async def test_refresh_token_success(client):
    create_user_response = await create_test_user(client)
    login_response = await client.post(
        "v1/auth/login",
        data={"username": create_user_response["email"], "password": "test_password"},
    )
    assert login_response.status_code == 200
    refresh_token = login_response.json()["refresh_token"]

    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": refresh_token}
    )
    assert response.status_code == 200
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert response.json()["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_refresh_token_invalid_refresh(client):
    response = await client.post(
        "/v1/auth/refresh", json={"refresh_token": "invalid_token"}
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Invalid refresh token"


@pytest.mark.asyncio
async def test_logout(client, db_session):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.post("/v1/auth/logout", headers=headers)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )

    assert user.refresh_token is None
    assert response.status_code == 200
    assert response.json()["message"] == "Logged out successfully"


@pytest.mark.asyncio
async def test_send_verification_email(client, db_session):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)
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
            headers=headers,
        )
    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    assert response.status_code == 200
    assert user.code_purpose == CodePurpose.verification_otp
    assert response.json()["message"] == "Verification code sent"
    mock_email.assert_called_once()
    mock_email.assert_called_once_with("test_user", "test@example.com", "123456")


@pytest.mark.asyncio
async def test_send_verification_email_to_already_verified_user(client, db_session):

    create_user_response = await create_test_user(client)
    await verify_user(create_user_response["id"], db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.post(
        "/v1/auth/verify_email",
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "User already verified"


@pytest.mark.asyncio
async def test_verify_email_confirm_success(client, db_session):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.code_purpose = CodePurpose.verification_otp
    await db_session.commit()

    response = await client.post(
        "/v1/auth/verify_email/confirm", json={"otp": "123456"}, headers=headers
    )
    await db_session.refresh(user)
    assert user.code_purpose is None
    assert response.status_code == 200
    assert response.json()["message"] == "Verification done"
    assert user.is_verified is True


@pytest.mark.asyncio
async def test_verify_email_confirm_wrong_otp(client, db_session):
    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.code_purpose = CodePurpose.verification_otp
    await db_session.commit()
    response = await client.post(
        "/v1/auth/verify_email/confirm", json={"otp": "000000"}, headers=headers
    )
    await db_session.refresh(user)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification code"
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_verify_email_confirm_expired_otp(client, db_session):
    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) - timedelta(
        minutes=10
    )  # intentionally set to 10 mins ago
    user.code_purpose = CodePurpose.verification_otp
    await db_session.commit()
    response = await client.post(
        "/v1/auth/verify_email/confirm", json={"otp": "000000"}, headers=headers
    )
    await db_session.refresh(user)

    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification code"
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_verify_email_of_already_verified_user(client, db_session):

    create_user_response = await create_test_user(client)
    await verify_user(create_user_response["id"], db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.post(
        "/v1/auth/verify_email/confirm",
        json={"otp": "123456"},
        headers=headers,
    )
    assert response.status_code == 409
    assert response.json()["detail"] == "User already verified"


@pytest.mark.asyncio
async def test_verify_email_invalid_input(client, db_session):
    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.code_purpose = CodePurpose.verification_otp
    await db_session.commit()

    response = await client.post(
        "/v1/auth/verify_email/confirm", json={}, headers=headers
    )
    await db_session.refresh(user)

    assert response.status_code == 422
    assert user.is_verified is False


@pytest.mark.asyncio
async def test_change_password_successfully(client, db_session):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.patch(
        "/v1/auth/change_password",
        json={
            "current_password": "test_password",
            "new_password": "new_password",
        },
        headers=headers,
    )
    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )

    assert verify_password("new_password", user.password_hash) is True
    assert verify_password("test_password", user.password_hash) is False
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_change_password_wrong_current_password(client):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.patch(
        "/v1/auth/change_password",
        json={
            "current_password": "wrong_password",
            "new_password": "new_password",
        },
        headers=headers,
    )
    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect current password"


@pytest.mark.asyncio
async def test_change_password_invalid_new_password(client):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.patch(
        "/v1/auth/change_password",
        json={
            "current_password": "test_password",
            "new_password": "123456",
        },
        headers=headers,
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_send_forgot_password_mail(client, db_session):

    create_user_response = await create_test_user(client)
    expires_at = datetime.now(UTC) + timedelta(minutes=10)

    with (
        patch(
            "src.auth.service.verification_code_generate",
            return_value=("123456", expires_at),
        ),
        patch("src.auth.service.send_password_reset_otp") as mock_email,
    ):
        response = await client.post(
            "/v1/auth/forgot_password", json={"email": create_user_response["email"]}
        )
    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )

    assert user.code_purpose == CodePurpose.password_reset
    assert response.status_code == 200
    assert (
        response.json()["message"]
        == "If an account with that email exists,a password reset email has been sent."
    )
    mock_email.assert_called_once()
    mock_email.assert_called_once_with("test_user", "test@example.com", "123456")


@pytest.mark.asyncio
async def test_reset_password_using_otp_success(client, db_session):

    create_user_response = await create_test_user(client)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.code_purpose = CodePurpose.password_reset
    await db_session.commit()

    response = await client.post(
        "/v1/auth/reset_password",
        json={
            "email": create_user_response["email"],
            "otp": "123456",
            "new_password": "new_password",
        },
    )

    await db_session.refresh(user)
    assert verify_password("new_password", user.password_hash) is True
    assert user.code_purpose is None
    assert response.status_code == 200
    assert response.json()["message"] == "Password changed"


@pytest.mark.asyncio
async def test_reset_password_using_otp_wrong_otp(client, db_session):

    create_user_response = await create_test_user(client)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.code_purpose = CodePurpose.password_reset
    await db_session.commit()
    response = await client.post(
        "/v1/auth/reset_password",
        json={
            "email": create_user_response["email"],
            "otp": "000000",
            "new_password": "new_password",
        },
    )

    await db_session.refresh(user)
    assert verify_password("new_password", user.password_hash) is False
    assert user.code_purpose is not None
    assert response.status_code == 400
    assert response.json()["detail"] == "Invalid or expired verification code"


@pytest.mark.asyncio
async def test_reset_password_using_otp_invalid_new_password(client, db_session):

    create_user_response = await create_test_user(client)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    user.verification_code = hash_password("123456")
    user.verification_expires_at = datetime.now(UTC) + timedelta(minutes=10)
    user.code_purpose = CodePurpose.password_reset
    await db_session.commit()
    response = await client.post(
        "/v1/auth/reset_password",
        json={
            "email": create_user_response["email"],
            "otp": "123456",
            "new_password": "abcdef",
        },
    )

    await db_session.refresh(user)
    assert verify_password("new_password", user.password_hash) is False
    assert user.code_purpose is not None
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_delete_unverified_account_success(client, db_session):
    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)

    response = await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "test_password",
        },
        headers=headers,
    )
    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    assert response.status_code == 200
    assert user is None
    assert response.json()["message"] == "Account_deleted"


@pytest.mark.asyncio
async def test_delete_verified_account_success(client, db_session):
    create_user_response = await create_test_user(client)
    await verify_user(create_user_response["id"], db_session)
    token = await login_user(client)
    headers = auth_headers(token)

    user = await db_session.scalar(
        select(User).where(User.id == create_user_response["id"])
    )
    assert user.is_verified is True
    assert user.is_deleted is False

    response = await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "test_password",
        },
        headers=headers,
    )
    await db_session.refresh(user)
    assert response.status_code == 200
    assert user is not None
    assert user.is_deleted is True


@pytest.mark.asyncio
async def test_delete_account_wrong_password(client):

    create_user_response = await create_test_user(client)
    token = await login_user(client)
    headers = auth_headers(token)
    response = await client.request(
        "DELETE",
        "/v1/auth/delete-account",
        json={
            "password": "wrong_password",
        },
        headers=headers,
    )

    assert response.status_code == 401
    assert response.json()["detail"] == "Incorrect password"
