"""Deliver outbound notifications and update NotificationLog."""
import logging

from django.conf import settings
from django.core.mail import send_mail

from apps.notifications.models import NotificationLog
from apps.notifications.services.push_provider import send_push
from apps.notifications.services.sms_provider import send_sms

logger = logging.getLogger(__name__)


def deliver_notification(log: NotificationLog) -> NotificationLog:
    """
    Send the notification for the given log row and persist status / provider ids.
    Safe to call when optional deps (Twilio, Firebase) are missing — log reflects failure.
    """
    try:
        if log.channel == "sms":
            result = send_sms(log.recipient.phone, log.body)
        elif log.channel == "push":
            token = (log.recipient.fcm_token or "").strip()
            if not token:
                result = {"success": False, "error": "recipient_has_no_fcm_token"}
            else:
                result = send_push(
                    token,
                    log.subject or "Nagrik Awaaz",
                    log.body,
                    data={"complaint_id": str(log.complaint_id)} if log.complaint_id else {},
                )
        elif log.channel == "email":
            result = _send_email(log)
        elif log.channel == "whatsapp":
            result = {"success": False, "error": "whatsapp_channel_not_configured"}
        else:
            result = {"success": False, "error": f"unsupported_channel:{log.channel}"}

        if result.get("success"):
            log.status = "sent"
            log.provider_message_id = str(result.get("provider_id", ""))[:255]
            log.error_message = ""
        else:
            log.status = "failed"
            log.error_message = str(result.get("error", "send_failed"))[:2000]
        log.save(update_fields=["status", "provider_message_id", "error_message", "updated_at"])
    except Exception as exc:  # noqa: BLE001 — last-resort so API still returns the log row
        logger.exception("deliver_notification failed for log %s: %s", log.pk, exc)
        log.status = "failed"
        log.error_message = str(exc)[:2000]
        log.save(update_fields=["status", "error_message", "updated_at"])

    return log


def _send_email(log: NotificationLog) -> dict:
    to = (log.recipient.email or "").strip()
    if not to:
        return {"success": False, "error": "recipient_has_no_email"}

    send_mail(
        subject=log.subject or "Nagrik Awaaz",
        message=log.body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[to],
        fail_silently=False,
    )
    return {"success": True, "provider_id": "django-send_mail"}
