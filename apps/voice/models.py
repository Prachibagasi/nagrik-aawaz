from django.db import models
from apps.core.models import TimeStampedModel


class VoiceJob(TimeStampedModel):
    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("processing", "Processing"),
        ("done", "Done"),
        ("failed", "Failed"),
    ]

    audio_file = models.FileField(upload_to="voice/jobs/%Y/%m/")
    language = models.CharField(max_length=5, default="hi")
    transcript = models.TextField(blank=True)
    confidence = models.FloatField(null=True, blank=True)
    provider = models.CharField(max_length=20, default="whisper")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default="pending")
    error_message = models.TextField(blank=True)
    duration_seconds = models.FloatField(null=True, blank=True)

    complaint = models.OneToOneField(
        "complaints.Complaint",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="voice_job",
    )
    submitted_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "voice_job"
        ordering = ["-created_at"]

    def __str__(self):
        return f"VoiceJob[{self.status}] {self.language} ({self.created_at:%Y-%m-%d})"
