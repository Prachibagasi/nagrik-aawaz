import pytest
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import RefreshToken

from apps.complaints.models import Category

User = get_user_model()

CATEGORY_FIXTURE = [
    {"name": "Roads & Potholes", "slug": "roads-potholes", "sort_order": 1},
    {"name": "Water Supply", "slug": "water-supply", "sort_order": 2},
    {"name": "Other", "slug": "other", "sort_order": 99},
]


@pytest.fixture
def api_client():
    from rest_framework.test import APIClient
    return APIClient()


@pytest.fixture
def categories(db):
    for row in CATEGORY_FIXTURE:
        Category.objects.update_or_create(
            slug=row["slug"],
            defaults={
                "name": row["name"],
                "sort_order": row["sort_order"],
                "is_active": True,
            },
        )
    return list(Category.objects.all())


@pytest.fixture
def user_citizen(db):
    return User.objects.create_user(
        phone="+919876543210",
        password="testpass123",
        full_name="Test Citizen",
        role="citizen",
    )


@pytest.fixture
def user_officer(db):
    return User.objects.create_user(
        phone="+919876543211",
        password="testpass123",
        full_name="Test Officer",
        role="officer",
        ward="Ward 1",
    )


@pytest.fixture
def user_admin(db):
    return User.objects.create_user(
        phone="+919876543212",
        password="testpass123",
        full_name="Test Admin",
        role="admin",
        is_staff=True,
    )


def bearer(user):
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}
