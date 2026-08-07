import pytest
from rest_framework_simplejwt.tokens import RefreshToken


def _auth(user):
    return {"HTTP_AUTHORIZATION": f"Bearer {RefreshToken.for_user(user).access_token}"}


@pytest.mark.django_db
def test_categories_public(api_client, categories):
    r = api_client.get("/api/v1/complaints/categories/")
    assert r.status_code == 200
    assert len(r.json()) >= 1


@pytest.mark.django_db
def test_create_complaint_hindi_typed(api_client, user_citizen, categories):
    r = api_client.post(
        "/api/v1/complaints/",
        {
            "description": "हमारे इलाके में पानी की आपूर्ति दो दिन से बंद है।",
            "description_language": "hi",
            "title": "पानी की समस्या",
            "city": "देहरादून",
            "source": "web",
            "is_anonymous": False,
        },
        format="json",
        **_auth(user_citizen),
    )
    assert r.status_code == 201
    data = r.json()["complaint"]
    assert data["description_language"] == "hi"
    assert "पानी" in data["description"]


@pytest.mark.django_db
def test_create_complaint_ai_category(api_client, user_citizen, categories):
    r = api_client.post(
        "/api/v1/complaints/",
        {
            "description": "There is no water supply in our area for two days.",
            "description_language": "en",
            "title": "Water outage",
            "city": "Pune",
            "source": "web",
            "is_anonymous": False,
        },
        format="json",
        **_auth(user_citizen),
    )
    assert r.status_code == 201
    data = r.json()["complaint"]
    assert data["category"]["name"] == "Water Supply"
    assert data["ai_category_confidence"] is not None


@pytest.mark.django_db
def test_track_complaint(api_client, user_citizen, categories):
    c = api_client.post(
        "/api/v1/complaints/",
        {
            "description": "Street light broken",
            "title": "Light",
            "city": "Pune",
            "source": "web",
            "is_anonymous": False,
        },
        format="json",
        **_auth(user_citizen),
    )
    tid = c.json()["tracking_id"]
    tr = api_client.get(f"/api/v1/complaints/track/{tid}/")
    assert tr.status_code == 200
    assert tr.json()["tracking_id"] == tid


@pytest.mark.django_db
def test_officer_status_update(api_client, user_citizen, user_officer, categories):
    c = api_client.post(
        "/api/v1/complaints/",
        {
            "description": "Garbage not collected",
            "city": "Pune",
            "source": "web",
            "is_anonymous": False,
        },
        format="json",
        **_auth(user_citizen),
    )
    cid = c.json()["complaint"]["id"]
    r = api_client.patch(
        f"/api/v1/complaints/{cid}/status/",
        {"status": "acknowledged", "note": "Seen"},
        format="json",
        **_auth(user_officer),
    )
    assert r.status_code == 200
    assert r.json()["status"] == "acknowledged"


@pytest.mark.django_db
def test_admin_assign(api_client, user_citizen, user_officer, user_admin, categories):
    c = api_client.post(
        "/api/v1/complaints/",
        {
            "description": "Pothole on main road",
            "city": "Pune",
            "source": "web",
            "is_anonymous": False,
        },
        format="json",
        **_auth(user_citizen),
    )
    cid = c.json()["complaint"]["id"]
    r = api_client.post(
        f"/api/v1/complaints/{cid}/assign/",
        {"officer_id": str(user_officer.id)},
        format="json",
        **_auth(user_admin),
    )
    assert r.status_code == 200


@pytest.mark.django_db
def test_check_duplicates_post(api_client, user_citizen, categories):
    """POST body avoids long-URL issues for duplicate check."""
    api_client.post(
        "/api/v1/complaints/",
        {
            "description": "Broken street light near park",
            "city": "Pune",
            "source": "web",
            "is_anonymous": False,
        },
        format="json",
        **_auth(user_citizen),
    )
    r = api_client.post(
        "/api/v1/complaints/check-duplicates/",
        {"description": "street light broken", "city": "Pune", "ward": ""},
        format="json",
        **_auth(user_citizen),
    )
    assert r.status_code == 200
    data = r.json()
    assert "possible_duplicates" in data
    assert data["count"] >= 0


@pytest.mark.django_db
def test_create_complaint_high_precision_gps_rounded(api_client, user_citizen, categories):
    """Browser GPS sends many fractional digits; model allows decimal_places=6."""
    r = api_client.post(
        "/api/v1/complaints/",
        {
            "description": "Potholes on ring road",
            "description_language": "en",
            "title": "Potholes",
            "city": "Pune",
            "source": "web",
            "is_anonymous": False,
            "latitude": 18.520430123456789,
            "longitude": 73.856743987654321,
        },
        format="json",
        **_auth(user_citizen),
    )
    assert r.status_code == 201, r.content
    c = r.json()["complaint"]
    assert float(c["latitude"]) == pytest.approx(18.520430, abs=1e-6)
    assert float(c["longitude"]) == pytest.approx(73.856744, abs=1e-6)


@pytest.mark.django_db
def test_mine_list(api_client, user_citizen, categories):
    api_client.post(
        "/api/v1/complaints/",
        {"description": "Test mine", "city": "X", "source": "web", "is_anonymous": False},
        format="json",
        **_auth(user_citizen),
    )
    r = api_client.get("/api/v1/complaints/mine/", **_auth(user_citizen))
    assert r.status_code == 200
    assert r.json()["count"] >= 1


def test_geo_ip_localhost_fallback(api_client):
    r = api_client.get("/api/v1/complaints/geo/ip/")
    assert r.status_code == 200
    body = r.json()
    assert body["accuracy"] == "approximate"
    assert body["latitude"] == pytest.approx(30.3165, abs=0.01)
    assert body["longitude"] == pytest.approx(78.0322, abs=0.01)
