import logging

from django.conf import settings
from django.contrib.auth import get_user_model
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from rest_framework_simplejwt.tokens import RefreshToken

from apps.core.permissions import IsAdmin
from .serializers import (
    UserRegistrationSerializer,
    UserSerializer,
    UserUpdateSerializer,
    ChangePasswordSerializer,
    SendOTPSerializer,
    VerifyOTPSerializer,
    AwaazTokenObtainSerializer,
)
from .services.auth_service import send_otp, mark_otp_used, verify_phone

logger = logging.getLogger(__name__)
User = get_user_model()


class RegisterView(APIView):
    """POST /api/v1/auth/register/ — public citizen registration."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        refresh = RefreshToken.for_user(user)
        return Response(
            {
                "message": "Registration successful.",
                "user": UserSerializer(user).data,
                "tokens": {
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                },
            },
            status=status.HTTP_201_CREATED,
        )


class AwaazTokenObtainView(TokenObtainPairView):
    """POST /api/v1/auth/login/ — returns JWT with role/name claims."""

    serializer_class = AwaazTokenObtainSerializer


class LogoutView(APIView):
    """POST /api/v1/auth/logout/ — blacklists the refresh token."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        refresh_token = request.data.get("refresh")
        if not refresh_token:
            return Response(
                {"error": {"code": "bad_request", "message": "Refresh token is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
        except Exception:
            pass  # Already blacklisted or invalid — treat as success
        return Response({"message": "Logged out successfully."}, status=status.HTTP_200_OK)


class MeView(APIView):
    """GET/PATCH /api/v1/auth/me/ — view or update own profile."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        return Response(UserSerializer(request.user).data)

    def patch(self, request):
        serializer = UserUpdateSerializer(
            request.user, data=request.data, partial=True
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(UserSerializer(request.user).data)


class ChangePasswordView(APIView):
    """POST /api/v1/auth/change-password/"""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        if not request.user.check_password(serializer.validated_data["current_password"]):
            return Response(
                {"error": {"code": "bad_request", "message": "Current password is incorrect."}},
                status=status.HTTP_400_BAD_REQUEST,
            )

        request.user.set_password(serializer.validated_data["new_password"])
        request.user.save(update_fields=["password"])
        return Response({"message": "Password updated successfully."})


class SendOTPView(APIView):
    """POST /api/v1/auth/otp/send/ — send OTP to phone number."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = SendOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        phone = serializer.validated_data["phone"]
        otp = send_otp(phone)

        logger.info("OTP for %s: %s", phone, otp)

        payload = {
            "message": f"OTP sent to {phone[-10:]}. Valid for 10 minutes.",
            "phone": phone,
        }
        # Dev / demo: show OTP when SMS is not configured (college demo without Twilio)
        if settings.DEBUG or not getattr(settings, "TWILIO_ACCOUNT_SID", "").strip():
            payload["dev_otp"] = otp

        return Response(payload, status=status.HTTP_200_OK)


class VerifyOTPView(APIView):
    """POST /api/v1/auth/otp/verify/ — verify OTP and mark phone verified."""

    permission_classes = [AllowAny]

    def post(self, request):
        serializer = VerifyOTPSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        otp_record = serializer.validated_data["otp_record"]
        mark_otp_used(otp_record)
        verify_phone(serializer.validated_data["phone"])

        return Response({"message": "Phone verified successfully."})


class UserListView(APIView):
    """GET /api/v1/auth/users/ — admin only: list all users."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def get(self, request):
        qs = User.objects.all().order_by("-created_at")
        serializer = UserSerializer(qs, many=True)
        return Response({"count": qs.count(), "results": serializer.data})
