"""Demo helpers: duplicate-style matches, past resolutions, SLA estimate."""
from datetime import timedelta

from django.utils import timezone

from apps.complaints.models import Complaint


def find_similar_complaints(description: str, city: str = "", ward: str = "", limit: int = 5):
    """Very simple similarity: overlapping substring + same city/ward when provided."""
    if not description or len(description.strip()) < 10:
        return Complaint.objects.none()

    q = description.strip()
    seed = q[:24].replace("\n", " ")
    qs = Complaint.objects.all().order_by("-created_at")
    if len(seed) >= 8:
        qs = qs.filter(description__icontains=seed[:12])
    if city:
        qs = qs.filter(city__icontains=city)
    if ward:
        qs = qs.filter(ward__icontains=ward)
    return qs[:limit]


def past_resolutions(category_id=None, city: str = "", limit: int = 5):
    qs = Complaint.objects.filter(status__in=("resolved", "closed")).select_related("category")
    if category_id:
        qs = qs.filter(category_id=category_id)
    if city:
        qs = qs.filter(city__icontains=city)
    return qs.order_by("-resolved_at", "-updated_at")[:limit]


def sla_estimate(complaint: Complaint) -> dict:
    """SLA-style estimate from category default_sla_days and submission time."""
    days = 7
    if complaint.category_id and complaint.category:
        days = int(complaint.category.default_sla_days or 7)
    start = complaint.created_at.date()
    expected = start + timedelta(days=days)
    today = timezone.now().date()
    overdue = today > expected and complaint.status not in ("resolved", "closed", "rejected")
    return {
        "category_sla_days": days,
        "submitted_on": str(start),
        "expected_resolution_by": str(expected),
        "is_overdue": overdue,
        "message": f"Typical resolution window for this category is about {days} working days (demo estimate).",
    }
