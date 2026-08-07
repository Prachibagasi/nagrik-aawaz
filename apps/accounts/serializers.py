from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

from .models import OTPVerification
from .validators import normalize_indian_phone, validate_email_format

User = get_user_model()


class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    confirm_password = serializers.CharField(write_only=True)
    otp = serializers.CharField(write_only=True, min_length=4, max_length=8)

    class Meta:
        model = User
        fields = [
            "phone", "full_name", "email", "password", "confirm_password",
            "preferred_language", "role", "otp",
        ]
        extra_kwargs = {
            "role": {"default": "citizen"},
            "email": {"required": False, "allow_blank": True},
        }

    def validate_phone(self, value):
        return normalize_indian_phone(value)

    def validate_email(self, value):
        if not value:
            return value
        return validate_email_format(value)

    def validate_role(self, value):
        # Public registration can only create citizens; officer/admin via admin panel
        if value not in ("citizen",):
            raise serializers.ValidationError("Self-registration supports 'citizen' role only.")
        return value

    def validate(self, attrs):
        if attrs["password"] != attrs.pop("confirm_password"):
            raise serializers.ValidationError({"confirm_password": "Passwords do not match."})

        phone = attrs["phone"]
        otp = attrs.pop("otp")
        now = timezone.now()
        record = (
            OTPVerification.objects.filter(
                phone=phone,
                otp=otp,
                is_used=False,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )
        if not record:
            raise serializers.ValidationError(
                {"otp": "Invalid or expired OTP. Tap Send OTP and try again."}
            )
        attrs["otp_record"] = record
        return attrs

    def create(self, validated_data):
        otp_record = validated_data.pop("otp_record")
        from .services.auth_service import mark_otp_used

        user = User.objects.create_user(**validated_data, is_phone_verified=True)
        mark_otp_used(otp_record)
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id", "phone", "full_name", "email", "role",
            "preferred_language", "ward", "department",
            "avatar", "is_phone_verified", "created_at",
        ]
        read_only_fields = ["id", "phone", "role", "is_phone_verified", "created_at"]


class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["full_name", "email", "preferred_language", "avatar", "fcm_token"]

    def validate_email(self, value):
        if not value:
            return value
        return validate_email_format(value)


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField(min_length=8)
    confirm_new_password = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["confirm_new_password"]:
            raise serializers.ValidationError({"confirm_new_password": "Passwords do not match."})
        return attrs


class SendOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()

    def validate_phone(self, value):
        return normalize_indian_phone(value)


class VerifyOTPSerializer(serializers.Serializer):
    phone = serializers.CharField()
    otp = serializers.CharField(min_length=4, max_length=8)

    def validate_phone(self, value):
        return normalize_indian_phone(value)

    def validate(self, attrs):
        now = timezone.now()
        record = (
            OTPVerification.objects.filter(
                phone=attrs["phone"],
                otp=attrs["otp"],
                is_used=False,
                expires_at__gt=now,
            )
            .order_by("-created_at")
            .first()
        )
        if not record:
            raise serializers.ValidationError({"otp": "Invalid or expired OTP."})
        attrs["otp_record"] = record
        return attrs


class AwaazTokenObtainSerializer(TokenObtainPairSerializer):
    """Extends the default JWT payload with role and name."""

    username_field = User.USERNAME_FIELD

    def validate(self, attrs):
        if User.USERNAME_FIELD in attrs:
            attrs[User.USERNAME_FIELD] = normalize_indian_phone(attrs[User.USERNAME_FIELD])
        return super().validate(attrs)

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token["role"] = user.role
        token["name"] = user.full_name
        token["phone"] = user.phone
        return token
