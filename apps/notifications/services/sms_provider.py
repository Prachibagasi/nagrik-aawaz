"""SMS notification service. Supports Twilio (default)."""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_sms(to_phone: str, message: str) -> dict:
    provider = getattr(settings, "SMS_PROVIDER", "twilio")
    if provider == "twilio":
        return _send_twilio(to_phone, message)
    logger.warning("Unknown SMS provider '%s'. Message not sent.", provider)
    return {"success": False, "error": "unknown_provider"}


def _send_twilio(to: str, body: str) -> dict:
    try:
        from twilio.rest import Client

        client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        msg = client.messages.create(body=body, from_=settings.TWILIO_PHONE_NUMBER, to=to)
        logger.info("SMS sent via Twilio: %s → %s", msg.sid, to)
        return {"success": True, "provider_id": msg.sid}

    except ImportError:
        logger.warning("twilio package not installed. SMS not sent to %s.", to)
        return {"success": False, "error": "twilio_not_installed"}
    except Exception as exc:
        logger.exception("Twilio SMS failed to %s: %s", to, exc)
        return {"success": False, "error": str(exc)}
