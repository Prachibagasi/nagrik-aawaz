from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework import status
from rest_framework.throttling import ScopedRateThrottle

from .serializers import (
    ClassifyRequestSerializer,
    TranslateRequestSerializer,
    ProcessComplaintRequestSerializer,
)
from .services.classifier import classify_text
from .services.agent1_pipeline import process_complaint
from .services.agent1_translator import translate_to_english
from apps.complaints.services.phase2.faq import match_faq
from apps.complaints.services.phase2.location_nlp import extract_places


class ClassifyTextView(APIView):
    """
    POST /api/v1/ai/classify/
    Body: { "text": "...", "language": "hi" }
    Returns: category, confidence, all_scores
    Full implementation in Module 6.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ClassifyRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        result = classify_text(
            text=serializer.validated_data["text"],
            language=serializer.validated_data.get("language", "en"),
        )

        return Response(result)


class TranslateTextView(APIView):
    """
    POST /api/v1/ai/translate/
    Demo stub: returns bracketed placeholder. Swap for Google Translate / indic-trans in production.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = TranslateRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        text = serializer.validated_data["text"]
        src = serializer.validated_data.get("source_language", "hi")
        tgt = serializer.validated_data.get("target_language", "en")
        translated = translate_to_english(text, src if src != tgt else src)
        return Response(
            {
                "translated_text": translated,
                "source_language": src,
                "target_language": tgt,
                "note": "Agent1 Groq translator when GROQ_API_KEY is set; otherwise passthrough/rules.",
            }
        )


class ProcessComplaintView(APIView):
    """
    POST /api/v1/ai/process-complaint/
    Full Agent1 pipeline: translate → classify → formal draft → department portal routing.
    """

    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ProcessComplaintRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        user = request.user
        name = data.get("complainant_name") or getattr(user, "full_name", "") or ""
        mobile = data.get("mobile") or getattr(user, "phone", "") or ""
        email = data.get("email") or getattr(user, "email", "") or ""
        if mobile.startswith("+"):
            mobile = mobile[-10:] if len(mobile) >= 10 else mobile.replace("+", "")

        try:
            result = process_complaint(
                data["text"],
                user_language=data.get("user_language") or "hi",
                complainant_name=name,
                mobile=mobile,
                email=email or "",
                title=data.get("title") or "",
                district=data.get("district") or data.get("city") or "",
                city=data.get("city") or "",
                ward=data.get("ward") or "",
                address=data.get("address") or "",
                pincode=data.get("pincode") or "",
                location=data.get("location") or "",
            )
        except ValueError as exc:
            return Response(
                {"error": {"code": "bad_request", "message": str(exc)}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(result, status=status.HTTP_200_OK)


class FAQQueryView(APIView):
    """
    POST /api/v1/ai/faq/query/
    Public throttled FAQ assistant (curate content in admin).
    """

    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "faq"

    def post(self, request):
        q = (request.data.get("query") or request.data.get("q") or "").strip()
        if len(q) < 2:
            return Response(
                {"error": {"code": "bad_request", "message": "query is too short."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(match_faq(q))


class ExtractLocationView(APIView):
    """POST /api/v1/ai/extract-location/ — speech / text location hints (Phase 2)."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        text = (request.data.get("text") or "").strip()
        if not text:
            return Response(
                {"error": {"code": "bad_request", "message": "text is required."}},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response({"extracted": extract_places(text), "text_length": len(text)})
