"""Indian mobile number normalization and validation."""
import re

from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

# Indian mobile: 10 digits, starts with 6–9
_INDIAN_MOBILE_RE = re.compile(r"^[6-9]\d{9}$")


def normalize_indian_phone(value: str) -> str:
    """
    Accept 10-digit mobile or +91 / 91 prefix; return +91XXXXXXXXXX.
    Raises serializers.ValidationError on invalid input.
    """
    raw = re.sub(r"[\s\-()]", "", str(value or "").strip())
    if not raw:
        raise serializers.ValidationError("Phone number is required.")

    if raw.startswith("+91"):
        digits = raw[3:]
    elif raw.startswith("91") and len(raw) == 12:
        digits = raw[2:]
    elif raw.startswith("0") and len(raw) == 11:
        digits = raw[1:]
    else:
        digits = raw

    if not _INDIAN_MOBILE_RE.match(digits):
        raise serializers.ValidationError(
            "Enter a valid 10-digit Indian mobile number (starts with 6, 7, 8, or 9)."
        )
    return f"+91{digits}"


def validate_email_format(value: str) -> str:
    """Require @ and a domain when email is provided."""
    if not value:
        return value
    email = str(value).strip()
    if "@" not in email:
        raise serializers.ValidationError("Enter a valid email address (must contain @).")
    local, _, domain = email.partition("@")
    if not local or not domain or "." not in domain:
        raise serializers.ValidationError("Enter a valid email address (e.g. name@example.com).")
    return email.lower()
