import random
import string
import logging
from datetime import timedelta

from django.utils import timezone
from django.contrib.auth import get_user_model

from apps.accounts.models import OTPVerification

logger = logging.getLogger(__name__)
User = get_user_model()

OTP_EXPIRY_MINUTES = 10


def generate_otp(length: int = 6) -> str:
    return "".join(random.choices(string.digits, k=length))


def send_otp(phone: str) -> str:
    """Generate and store OTP; return the code (caller sends via SMS)."""
    otp = generate_otp()
    expires_at = timezone.now() + timedelta(minutes=OTP_EXPIRY_MINUTES)

    OTPVerification.objects.create(phone=phone, otp=otp, expires_at=expires_at)

    # Invalidate stale OTPs for this phone (expired or superseded)
    OTPVerification.objects.filter(
        phone=phone, is_used=False, expires_at__lt=timezone.now()
    ).update(is_used=True)
    OTPVerification.objects.filter(phone=phone, is_used=False).exclude(otp=otp).update(
        is_used=True
    )

    logger.info("OTP generated for %s (expires %s)", phone, expires_at)

    from django.conf import settings

    if getattr(settings, "TWILIO_ACCOUNT_SID", "").strip():
        from apps.notifications.services.sms_provider import send_sms

        send_sms(phone, f"Your Nagrik Awaaz verification OTP is {otp}. Valid for {OTP_EXPIRY_MINUTES} minutes.")

    return otp


def mark_otp_used(otp_record: OTPVerification) -> None:
    otp_record.is_used = True
    otp_record.save(update_fields=["is_used"])


def verify_phone(phone: str) -> None:
    User.objects.filter(phone=phone).update(is_phone_verified=True)
