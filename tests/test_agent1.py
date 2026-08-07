import pytest

from conftest import bearer


@pytest.mark.django_db
def test_process_complaint_pwd_pothole(api_client, user_citizen):
    r = api_client.post(
        "/api/v1/ai/process-complaint/",
        {
            "text": "Hamare mohalle ki sadak me bahut bade gaddhe ho gaye hain, accident ho sakta hai",
            "user_language": "hi",
            "city": "Dehradun",
        },
        format="json",
        **bearer(user_citizen),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["department"] == "PWD"
    assert body["complaint_id"].startswith("COMP-")
    assert "draft_letter" in body and len(body["draft_letter"]) > 50
    assert body["portal"]["key"] == "pwd"
    assert body["portal"]["form_payload"]["portal_key"] == "pwd"
    assert "nagrik_complaint_id" in body["portal"]["form_payload"]


@pytest.mark.django_db
def test_process_complaint_electricity(api_client, user_citizen):
    r = api_client.post(
        "/api/v1/ai/process-complaint/",
        {"text": "No electricity in our colony since morning transformer failed", "user_language": "en"},
        format="json",
        **bearer(user_citizen),
    )
    assert r.status_code == 200
    assert r.json()["department"] == "Electricity"
    assert r.json()["portal"]["key"] == "bijli"


@pytest.mark.django_db
def test_process_complaint_rolls_typo_routes_pwd(api_client, user_citizen):
    """Typo 'rolls' for roads must not route to Education + electricity subcategory."""
    r = api_client.post(
        "/api/v1/ai/process-complaint/",
        {
            "text": "In my area rolls are very damaged and in bad condition.",
            "user_language": "en",
            "city": "Dehradun",
            "title": "Broken roads in colony",
        },
        format="json",
        **bearer(user_citizen),
    )
    assert r.status_code == 200
    body = r.json()
    assert body["department"] == "PWD"
    assert body["subcategory"] == "Road Pothole"
    assert body["portal"]["key"] == "pwd"
    assert "rolls are very damaged" in body["draft_letter"].lower() or "damaged" in body["draft_letter"].lower()
    assert "No Power Supply" not in body["draft_letter"]
    assert "Education" not in body["draft_letter"].split("Subject:")[1].split("\n")[0]


@pytest.mark.django_db
def test_department_api_post_pwd(api_client):
    r = api_client.post(
        "/api/v1/departments/pwd/complaints/",
        {
            "name": "Test User",
            "mobile": "9876543210",
            "district": "Dehradun",
            "category": "Road Damage / Pothole",
            "location": "MG Road",
            "description": "Test from pytest",
            "nagrik_complaint_id": "COMP-TEST-0001",
        },
        format="json",
    )
    assert r.status_code == 201
    body = r.json()
    assert body["id"].startswith("PWD-")
    assert body["nagrik_complaint_id"] == "COMP-TEST-0001"

    listed = api_client.get("/api/v1/departments/pwd/complaints/")
    assert listed.status_code == 200
    assert any(x["id"] == body["id"] for x in listed.json())
