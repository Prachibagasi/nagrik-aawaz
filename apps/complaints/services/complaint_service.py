import logging
from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.complaints.models import Complaint, ComplaintStatusHistory
from apps.complaints.services.status_notifications import notify_complaint_status_change

logger = logging.getLogger(__name__)
User = get_user_model()


def update_complaint_status(
    complaint: Complaint,
    new_status: str,
    changed_by,
    note: str = "",
    priority: str = None,
) -> Complaint:
    old_status = complaint.status

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status=old_status,
        new_status=new_status,
        changed_by=changed_by,
        note=note,
    )

    complaint.status = new_status
    if priority:
        complaint.priority = priority

    if new_status == "resolved" and not complaint.resolved_at:
        complaint.resolved_at = timezone.now()

    complaint.save(update_fields=["status", "priority", "resolved_at", "updated_at"])
    logger.info(
        "Complaint %s: %s → %s by user %s",
        complaint.tracking_id, old_status, new_status, changed_by,
    )
    notify_complaint_status_change(complaint, old_status, new_status)
    return complaint


def assign_complaint(complaint: Complaint, officer_id, due_date=None, assigned_by=None) -> Complaint:
    try:
        officer = User.objects.get(id=officer_id, role__in=("officer", "admin"))
    except User.DoesNotExist:
        raise ValueError(f"Officer {officer_id} not found or not an officer.")

    complaint.assigned_to = officer
    if due_date:
        complaint.due_date = due_date

    update_fields = ["assigned_to", "updated_at"]
    if due_date:
        update_fields.append("due_date")
    complaint.save(update_fields=update_fields)

    ComplaintStatusHistory.objects.create(
        complaint=complaint,
        old_status=complaint.status,
        new_status=complaint.status,
        changed_by=assigned_by,
        note=f"Assigned to {officer.full_name}",
    )
    return complaint


def upvote_complaint(complaint: Complaint, user) -> int:
    from apps.complaints.models import ComplaintUpvote

    _, created = ComplaintUpvote.objects.get_or_create(complaint=complaint, user=user)
    if created:
        Complaint.objects.filter(pk=complaint.pk).update(upvote_count=complaint.upvote_count + 1)
        complaint.upvote_count += 1
    return complaint.upvote_count


def get_complaint_stats(queryset=None) -> dict:
    if queryset is None:
        queryset = Complaint.objects.all()

    from django.db.models import Count
    stats = queryset.aggregate(
        total=Count("id"),
    )
    status_breakdown = (
        queryset.values("status").annotate(count=Count("id")).order_by("status")
    )
    category_breakdown = (
        queryset.values("category__name").annotate(count=Count("id")).order_by("-count")[:10]
    )
    return {
        "total": stats["total"],
        "by_status": {s["status"]: s["count"] for s in status_breakdown},
        "top_categories": list(category_breakdown),
    }
