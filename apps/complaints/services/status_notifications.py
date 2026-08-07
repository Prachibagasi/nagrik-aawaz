"""Notify citizens when complaint status changes (email when available)."""
import logging

from django.conf import settings

logger = logging.getLogger(__name__)


def notify_complaint_status_change(complaint, old_status: str, new_status: str) -> None:
    if old_status == new_status:
        return
    user = complaint.user
    if not user:
        return
    if not getattr(user, "email", None) or not str(user.email).strip():
        logger.info("Skip status email for %s — user has no email", complaint.tracking_id)
        return

    try:
        from apps.notifications.models import NotificationLog
        from apps.notifications.services.delivery import deliver_notification

        body = (
            f"Your complaint {complaint.tracking_id} has been updated.\n\n"
            f"Previous status: {old_status}\n"
            f"Current status: {new_status}\n\n"
            f"— Nagrik Awaaz"
        )
        log = NotificationLog.objects.create(
            recipient=user,
            complaint=complaint,
            channel="email",
            subject=f"Update: {complaint.tracking_id} is now {new_status}",
            body=body,
        )
        deliver_notification(log)
    except Exception as exc:  # noqa: BLE001
        logger.exception("notify_complaint_status_change failed: %s", exc)
