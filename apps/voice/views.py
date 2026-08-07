import logging
from django.shortcuts import get_object_or_404
from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser

from apps.core.pagination import StandardResultsPagination
from .models import VoiceJob
from .serializers import VoiceJobSerializer, TranscribeRequestSerializer
from .services.stt_whisper import transcribe_audio
from .services.audio_utils import get_audio_duration

logger = logging.getLogger(__name__)


class TranscribeView(APIView):
    """
    POST /api/v1/voice/transcribe/

    Multipart fields:
      audio_file  — audio file (mp3/wav/ogg/webm/m4a)
      language    — BCP-47 code (hi, en, ta …); default: hi
      complaint_id — optional UUID to link transcript to an existing complaint

    Returns transcript, detected language, and a voice_job id for later retrieval.
    """

    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request):
        serializer = TranscribeRequestSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        job = serializer.save()

        # Capture duration before transcription (file is on disk after save)
        try:
            job.duration_seconds = get_audio_duration(job.audio_file.path)
            job.save(update_fields=["duration_seconds"])
        except Exception:
            pass

        result = transcribe_audio(job)

        # If linked to a complaint, back-fill description from transcript
        if job.complaint and result.get("transcript"):
            complaint = job.complaint
            if not complaint.description:
                complaint.description = result["transcript"]
                complaint.description_language = result.get("language", job.language)
                complaint.save(update_fields=["description", "description_language", "updated_at"])

        return Response(
            {
                "job_id": str(job.id),
                "status": job.status,
                "transcript": result.get("transcript", ""),
                "language": result.get("language", job.language),
                "confidence": result.get("confidence"),
                "duration_seconds": job.duration_seconds,
                "stub_transcript": bool(result.get("stub_transcript")),
                "transcription_failed": bool(result.get("transcription_failed")),
                "user_message": result.get("user_message", ""),
            },
            status=status.HTTP_200_OK,
        )


class VoiceJobListView(APIView):
    """GET /api/v1/voice/jobs/ — list own voice jobs with pagination."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = VoiceJob.objects.filter(submitted_by=request.user).order_by("-created_at")
        paginator = StandardResultsPagination()
        page = paginator.paginate_queryset(qs, request)
        return paginator.get_paginated_response(VoiceJobSerializer(page, many=True).data)


class VoiceJobDetailView(APIView):
    """GET /api/v1/voice/jobs/<uuid>/ — single job detail."""

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        job = get_object_or_404(VoiceJob, pk=pk, submitted_by=request.user)
        return Response(VoiceJobSerializer(job).data)


class SupportedLanguagesView(APIView):
    """GET /api/v1/voice/languages/ — list supported STT languages."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        from django.conf import settings
        return Response(
            [
                {"code": code, "name": name}
                for code, name in settings.SUPPORTED_LANGUAGES.items()
            ]
        )
