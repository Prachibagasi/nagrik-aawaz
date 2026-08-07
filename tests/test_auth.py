import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


def _send_otp(api_client, phone):
    r = api_client.post("/api/v1/auth/otp/send/", {"phone": phone}, format="json")
    assert r.status_code == 200
    return r.json().get("dev_otp")


@pytest.mark.django_db
def test_register_login_me_logout(api_client):
    phone = "8888777666"
    otp = _send_otp(api_client, phone)
    assert otp

    reg = api_client.post(
        "/api/v1/auth/register/",
        {
            "phone": phone,
            "full_name": "New User",
            "password": "securepass1",
            "confirm_password": "securepass1",
            "preferred_language": "hi",
            "role": "citizen",
            "otp": otp,
        },
        format="json",
    )
    assert reg.status_code == 201
    assert reg.json()["user"]["is_phone_verified"] is True
    access = reg.json()["tokens"]["access"]

    me = api_client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access}")
    assert me.status_code == 200
    assert me.json()["phone"] == "+918888777666"

    refresh = reg.json()["tokens"]["refresh"]
    out = api_client.post(
        "/api/v1/auth/logout/",
        {"refresh": refresh},
        HTTP_AUTHORIZATION=f"Bearer {access}",
        format="json",
    )
    assert out.status_code == 200


@pytest.mark.django_db
def test_register_logout_login_me_again(api_client):
    """After logout (refresh blacklisted), a fresh login must issue new tokens and /me/ must work."""
    phone = "8888111222"
    password = "securepass1"
    otp = _send_otp(api_client, phone)
    reg = api_client.post(
        "/api/v1/auth/register/",
        {
            "phone": phone,
            "full_name": "Cycle User",
            "password": password,
            "confirm_password": password,
            "preferred_language": "hi",
            "role": "citizen",
            "otp": otp,
        },
        format="json",
    )
    assert reg.status_code == 201
    stored_phone = reg.json()["user"]["phone"]
    access1 = reg.json()["tokens"]["access"]
    refresh1 = reg.json()["tokens"]["refresh"]

    out = api_client.post(
        "/api/v1/auth/logout/",
        {"refresh": refresh1},
        HTTP_AUTHORIZATION=f"Bearer {access1}",
        format="json",
    )
    assert out.status_code == 200

    log = api_client.post(
        "/api/v1/auth/login/",
        {"phone": phone, "password": password},
        format="json",
    )
    assert log.status_code == 200
    access2 = log.json()["access"]
    assert access2 != access1

    me = api_client.get("/api/v1/auth/me/", HTTP_AUTHORIZATION=f"Bearer {access2}")
    assert me.status_code == 200
    assert me.json()["phone"] == stored_phone


@pytest.mark.django_db
def test_login_jwt(api_client, user_citizen):
    r = api_client.post(
        "/api/v1/auth/login/",
        {"phone": user_citizen.phone, "password": "testpass123"},
        format="json",
    )
    assert r.status_code == 200
    body = r.json()
    assert "access" in body and "refresh" in body


@pytest.mark.django_db
def test_phone_validation_10_digits(api_client):
    r = api_client.post(
        "/api/v1/auth/otp/send/",
        {"phone": "12345"},
        format="json",
    )
    assert r.status_code == 400


@pytest.mark.django_db
def test_email_validation(api_client):
    phone = "9876512345"
    otp = _send_otp(api_client, phone)
    r = api_client.post(
        "/api/v1/auth/register/",
        {
            "phone": phone,
            "full_name": "Bad Email",
            "email": "notanemail",
            "password": "securepass1",
            "confirm_password": "securepass1",
            "preferred_language": "hi",
            "role": "citizen",
            "otp": otp,
        },
        format="json",
    )
    assert r.status_code == 400
    details = r.json().get("error", {}).get("details", r.json())
    assert "email" in details


@pytest.mark.django_db
def test_login_with_10_digit_phone(api_client, user_citizen):
    digits = user_citizen.phone[-10:]
    r = api_client.post(
        "/api/v1/auth/login/",
        {"phone": digits, "password": "testpass123"},
        format="json",
    )
    assert r.status_code == 200
