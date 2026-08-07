import io
import pytest
from rest_framework_simplejwt.tokens import RefreshToken


def _auth(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


@pytest.mark.django_db
def test_classify(api_client, user_citizen):
    r = api_client.post(
        "/api/v1/ai/classify/",
        {"text": "The street dogs are barking all night near my house.", "language": "en"},
        format="json",
        **_auth(user_citizen),
    )
    assert r.status_code == 200
    body = r.json()
    assert "category" in body
    assert "confidence" in body


@pytest.mark.django_db
def test_voice_languages(api_client, user_citizen):
    r = api_client.get("/api/v1/voice/languages/", **_auth(user_citizen))
    assert r.status_code == 200
    assert isinstance(r.json(), list)
    assert any(x["code"] == "hi" for x in r.json())


@pytest.mark.django_db
def test_voice_transcribe_stub(api_client, user_citizen, settings):
    settings.STT_PROVIDER = "whisper"
    fake = io.BytesIO(b"fake audio content for stub")
    fake.name = "test.mp3"
    r = api_client.post(
        "/api/v1/voice/transcribe/",
        {"audio_file": fake, "language": "hi"},
        format="multipart",
        **_auth(user_citizen),
    )
    assert r.status_code == 200
    body = r.json()
    assert "job_id" in body
    assert "transcript" in body


@pytest.mark.django_db
def test_notification_send_email(api_client, user_admin, user_citizen):
    user_citizen.email = "citizen@example.com"
    user_citizen.save(update_fields=["email"])
    r = api_client.post(
        "/api/v1/notifications/send/",
        {
            "recipient_phone": user_citizen.phone,
            "channel": "email",
            "subject": "Test",
            "body": "Hello from test",
        },
        format="json",
        **_auth(user_admin),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "sent"
