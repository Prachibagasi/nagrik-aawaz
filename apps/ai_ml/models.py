from django.db import models
from apps.core.models import TimeStampedModel


class ClassificationResult(TimeStampedModel):
    """Stores each AI classification run for auditing and retraining."""

    complaint = models.ForeignKey(
        "complaints.Complaint",
        on_delete=models.CASCADE,
        related_name="classifications",
    )
    input_text = models.TextField()
    predicted_category = models.CharField(max_length=100)
    confidence = models.FloatField()
    all_scores = models.JSONField(default=dict, help_text="Full category → score map")
    model_version = models.CharField(max_length=50, default="v1")
    accepted = models.BooleanField(null=True, blank=True, help_text="Did officer accept this prediction?")

    class Meta:
        db_table = "ai_ml_classification"
        ordering = ["-created_at"]
