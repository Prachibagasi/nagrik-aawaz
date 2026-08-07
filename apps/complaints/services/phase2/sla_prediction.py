"""SLA prediction — queue-aware, priority-aware extension beyond static category SLA days."""
from __future__ import annotations

from datetime import timedelta
from typing import Any, Dict, List

from django.conf import settings
from django.db.models import Avg, Count, Q
from django.db.models.functions import TruncDate
from django.utils import timezone

from apps.complaints.models import Complaint


def _open_complaints_count() -> int:
    return Complaint.objects.filter(
        ~Q(status__in=("resolved", "closed", "rejected"))
    ).count()


def predict_sla_full(complaint: Complaint) -> Dict[str, Any]:
    """
    Production-style structured prediction with explicit factors (auditable).
    """
    cat_days = 7
    if complaint.category_id and complaint.category:
        cat_days = int(complaint.category.default_sla_days or 7)

    backlog = _open_complaints_count()
    sens = float(getattr(settings, "PHASE2_SLA_QUEUE_SENSITIVITY", 0.002))
    queue_factor = 1.0 + min(0.45, backlog * sens)

    pmult = {
        "critical": 0.72,
        "high": 0.88,
        "normal": 1.0,
        "low": 1.12,
    }.get(complaint.priority, 1.0)

    urgency = complaint.urgency_score
    urgency_factor = 1.0
    if urgency is not None:
        urgency_factor = max(0.78, min(1.18, 1.05 - float(urgency) * 0.15))

    sentiment = complaint.sentiment_score
    stress_factor = 1.0
    if sentiment is not None and sentiment < -0.25:
        stress_factor = 0.92

    predicted_calendar_days = max(
        1,
        int(round(cat_days * queue_factor * pmult * urgency_factor * stress_factor)),
    )

    start = complaint.created_at.date()
    expected = start + timedelta(days=predicted_calendar_days)
    today = timezone.now().date()
    overdue = today > expected and complaint.status not in ("resolved", "closed", "rejected")

    confidence = 0.65
    if complaint.category_id and complaint.ward:
        confidence = min(0.92, confidence + 0.12)

    return {
        "category_baseline_days": cat_days,
        "predicted_calendar_days": predicted_calendar_days,
        "expected_resolution_by": str(expected),
        "submitted_on": str(start),
        "is_overdue": overdue,
        "confidence": round(confidence, 3),
        "factors": {
            "open_complaints_backlog": backlog,
            "queue_factor": round(queue_factor, 4),
            "priority_multiplier": pmult,
            "urgency_multiplier": round(urgency_factor, 4),
            "stress_multiplier": round(stress_factor, 4),
        },
        "message": (
            f"Estimated resolution window ~{predicted_calendar_days} calendar days "
            f"(category baseline {cat_days}d, adjusted for backlog and priority)."
        ),
    }


def sentiment_trend_series(days: int = 14) -> List[Dict[str, Any]]:
    """Daily buckets for admin sentiment dashboard (all complaints with scores)."""
    since = timezone.now() - timedelta(days=days)
    rows = (
        Complaint.objects.filter(created_at__gte=since)
        .exclude(sentiment_score__isnull=True)
        .annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(count=Count("id"), avg_sentiment=Avg("sentiment_score"))
        .order_by("day")
    )
    return [
        {
            "date": r["day"].isoformat() if r["day"] else None,
            "count": r["count"],
            "avg_sentiment": round(r["avg_sentiment"] or 0, 4),
        }
        for r in rows
    ]
