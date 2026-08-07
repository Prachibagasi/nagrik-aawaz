import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.complaints.models import Complaint, FAQEntry
from apps.complaints.services.phase2.clustering import compute_cluster_key
from apps.complaints.services.phase2.faq import match_faq
from apps.complaints.services.phase2.sla_prediction import predict_sla_full, sentiment_trend_series
from apps.complaints.services.phase2.sentiment import score_text

User = get_user_model()


def test_cluster_key_stable():
    k1 = compute_cluster_key(
        "Big pothole near school gate broken road",
        "Pune",
        "Ward 12",
    )
    k2 = compute_cluster_key(
        "Big pothole near school gate broken road",
        "Pune",
        "Ward 12",
    )
    assert k1 == k2 and len(k1) == 32


def test_sentiment_range():
    s = score_text("Everything is broken urgent dangerous garbage everywhere!!!")
    assert -1.0 <= s <= 1.0


@pytest.mark.django_db
def test_faq_match_returns_answer():
    FAQEntry.objects.create(
        question="Track complaint?",
        keywords="track",
        answer="Use tracking ID.",
        sort_order=0,
    )
    out = match_faq("how to track my complaint")
    assert out["matches"]
    assert "tracking" in out["matches"][0]["answer"].lower()


@pytest.mark.django_db
def test_sla_prediction_shape(user_citizen):
    c = Complaint.objects.create(
        user=user_citizen,
        description="Road damage",
        city="Pune",
        ward="W1",
        title="Road",
    )
    out = predict_sla_full(c)
    assert "predicted_calendar_days" in out
    assert "factors" in out
    assert out["confidence"] <= 1.0


@pytest.mark.django_db
def test_sentiment_trend_series_empty_ok():
    assert sentiment_trend_series(days=7) == []


@pytest.mark.django_db
def test_faq_api_public(api_client):
    r = api_client.post("/api/v1/ai/faq/query/", {"query": "track complaint"}, format="json")
    assert r.status_code == 200
    assert "matches" in r.json()


@pytest.mark.django_db
def test_faq_match_hindi_status():
    FAQEntry.objects.create(
        question="Test Hindi?",
        keywords="शिकायत, स्थिति, ट्रैक",
        answer="Hindi answer about status.",
        sort_order=0,
    )
    out = match_faq("शिकायत की स्थिति")
    assert out["matches"]
    assert "Hindi" in out["matches"][0]["answer"] or "status" in out["matches"][0]["answer"].lower()


@pytest.mark.django_db
def test_faq_fallback_when_empty_db():
    out = match_faq("something random xyz")
    assert out["matches"]
    assert out["matches"][0]["id"] == "fallback-status"


@pytest.mark.django_db
def test_extract_location_auth(api_client, user_citizen):
    api_client.force_authenticate(user=user_citizen)
    r = api_client.post(
        "/api/v1/ai/extract-location/",
        {"text": "Near MG Road pincode 411001"},
        format="json",
    )
    assert r.status_code == 200
    assert "extracted" in r.json()


@pytest.mark.django_db
def test_ivr_stub(api_client):
    r = api_client.post("/api/v1/integrations/ivr/inbound/", {"from": "+91999"}, format="json")
    assert r.status_code == 200
    assert r.json().get("status") == "received"
