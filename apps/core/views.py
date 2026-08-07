from django.db import connection
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import ScopedRateThrottle


class HealthView(APIView):
    """GET /api/v1/health/ — public liveness; optional DB check."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def get(self, request):
        db_ok = True
        try:
            connection.ensure_connection()
        except Exception:  # noqa: BLE001
            db_ok = False
        payload = {
            "status": "ok" if db_ok else "degraded",
            "database": db_ok,
        }
        return Response(payload, status=200 if db_ok else 503)


class IVRInboundStubView(APIView):
    """
    POST /api/v1/integrations/ivr/inbound/
    Structured webhook placeholder for telecom / Twilio IVR — validate signature in production.
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "integrations"

    def post(self, request):
        return Response(
            {
                "status": "received",
                "message": "IVR adapter not fully configured. Map this URL to your telephony provider "
                "and create complaints from ASR text in a background worker.",
                "echo": {
                    "from": request.data.get("from") or request.data.get("caller_id"),
                    "language": request.data.get("language"),
                },
            },
            status=200,
        )
