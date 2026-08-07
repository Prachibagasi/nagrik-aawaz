from rest_framework import serializers
from django.conf import settings
from .models import VoiceJob
from .services.audio_utils import validate_audio_file, AudioValidationError

SUPPORTED_LANGUAGES = getattr(settings, "SUPPORTED_LANGUAGES", {})


class VoiceJobSerializer(serializers.ModelSerializer):
    class Meta:
        model = VoiceJob
        fields = [
            "id", "language", "transcript", "confidence",
            "provider", "status", "duration_seconds", "error_message",
            "created_at",
        ]
        read_only_fields = fields


class TranscribeRequestSerializer(serializers.Serializer):
    audio_file = serializers.FileField()
    language = serializers.CharField(max_length=5, default="hi")
    complaint_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_language(self, value):
        if SUPPORTED_LANGUAGES and value not in SUPPORTED_LANGUAGES:
            raise serializers.ValidationError(
                f"Unsupported language '{value}'. Supported: {', '.join(SUPPORTED_LANGUAGES)}"
            )
        return value

    def validate_audio_file(self, file):
        try:
            validate_audio_file(file)
        except AudioValidationError as exc:
            raise serializers.ValidationError(str(exc))
        return file

    def create(self, validated_data):
        from apps.complaints.models import Complaint

        user = self.context["request"].user
        complaint = None
        complaint_id = validated_data.pop("complaint_id", None)
        if complaint_id:
            try:
                complaint = Complaint.objects.get(pk=complaint_id, user=user)
            except Complaint.DoesNotExist:
                pass

        job = VoiceJob.objects.create(
            submitted_by=user,
            complaint=complaint,
            **validated_data,
        )
        return job
