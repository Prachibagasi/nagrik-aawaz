"""Rule-based smart assignment: ward / department / lowest workload."""
from __future__ import annotations

import logging
from typing import Optional

from django.conf import settings
from django.contrib.auth import get_user_model
from django.db.models import Count, Q

from apps.complaints.models import Complaint
from apps.complaints.services.complaint_service import assign_complaint

logger = logging.getLogger(__name__)
User = get_user_model()

ACTIVE_ASSIGNMENT = Q(
    assigned_complaints__status__in=("submitted", "acknowledged", "in_progress")
)


def suggest_assignee(complaint: Complaint) -> Optional[User]:
    """
    Pick the best-matching active officer. Deterministic, explainable rules.
    """
    base = User.objects.filter(role="officer", is_active=True)
    if not base.exists():
        base = User.objects.filter(role="admin", is_active=True)
    if not base.exists():
        return None

    ward = (complaint.ward or "").strip()
    if ward:
        wq = (
            base.filter(ward__iexact=ward)
            .annotate(open_load=Count("assigned_complaints", filter=ACTIVE_ASSIGNMENT))
            .order_by("open_load", "phone")
        )
        if wq.exists():
            return wq.first()

    cat_name = ""
    if complaint.category:
        cat_name = (complaint.category.name or "").strip()
    if cat_name:
        token = cat_name.split()[0]
        dq = (
            base.filter(department__icontains=token)
            .annotate(open_load=Count("assigned_complaints", filter=ACTIVE_ASSIGNMENT))
            .order_by("open_load", "phone")
        )
        if dq.exists():
            return dq.first()

    return (
        base.annotate(open_load=Count("assigned_complaints", filter=ACTIVE_ASSIGNMENT))
        .order_by("open_load", "phone")
        .first()
    )


def try_auto_assign(complaint: Complaint) -> bool:
    """Assign only when enabled and complaint has no assignee."""
    if not getattr(settings, "PHASE2_AUTO_ASSIGN_ENABLED", False):
        return False
    if complaint.assigned_to_id:
        return False
    officer = suggest_assignee(complaint)
    if not officer:
        logger.info("Auto-assign: no candidate for %s", complaint.tracking_id)
        return False
    assign_complaint(complaint, officer.id, assigned_by=None)
    logger.info(
        "Auto-assigned %s → officer %s",
        complaint.tracking_id,
        officer.phone,
    )
    return True
