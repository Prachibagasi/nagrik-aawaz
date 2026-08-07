"""Firebase Cloud Messaging push notification service."""
import logging
from django.conf import settings

logger = logging.getLogger(__name__)


def send_push(fcm_token: str, title: str, body: str, data: dict = None) -> dict:
    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        if not firebase_admin._apps:
            cred = credentials.Certificate(settings.FIREBASE_CREDENTIALS_PATH)
            firebase_admin.initialize_app(cred)

        message = messaging.Message(
            notification=messaging.Notification(title=title, body=body),
            data={k: str(v) for k, v in (data or {}).items()},
            token=fcm_token,
        )
        response = messaging.send(message)
        logger.info("Push sent: %s → token ending %s", response, fcm_token[-6:])
        return {"success": True, "provider_id": response}

    except ImportError:
        logger.warning("firebase-admin not installed. Push not sent.")
        return {"success": False, "error": "firebase_admin_not_installed"}
    except Exception as exc:
        logger.exception("Push notification failed: %s", exc)
        return {"success": False, "error": str(exc)}
