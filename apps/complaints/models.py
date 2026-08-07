import uuid
from django.conf import settings
from django.db import models

from apps.core.models import TimeStampedModel


def _default_empty_list():
    return []


class Category(models.Model):
    """Complaint categories (seeded, not user-created)."""

    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(unique=True)
    icon = models.CharField(max_length=50, blank=True, help_text="Icon name / emoji")
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    default_sla_days = models.PositiveSmallIntegerField(default=7)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "complaints_category"
        verbose_name_plural = "Categories"
        ordering = ["sort_order", "name"]

    def __str__(self):
        return self.name


class Complaint(TimeStampedModel):
    STATUS_CHOICES = [
        ("submitted", "Submitted"),
        ("acknowledged", "Acknowledged"),
        ("in_progress", "In Progress"),
        ("resolved", "Resolved"),
        ("closed", "Closed"),
        ("rejected", "Rejected"),
    ]

    PRIORITY_CHOICES = [
        ("low", "Low"),
        ("normal", "Normal"),
        ("high", "High"),
        ("critical", "Critical"),
    ]

    SOURCE_CHOICES = [
        ("web", "Web App"),
        ("mobile", "Mobile App"),
        ("whatsapp", "WhatsApp"),
        ("ivr", "IVR / Phone Call"),
        ("api", "API"),
    ]

    # Identity & ownership
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="complaints",
    )
    tracking_id = models.CharField(
        max_length=12,
        unique=True,
        db_index=True,
        editable=False,
        help_text="Human-readable ticket number (e.g. NA-00001234)",
    )

    # Content
    title = models.CharField(max_length=255, blank=True)
    description = models.TextField(help_text="Original complaint text (may be transcribed voice)")
    description_language = models.CharField(max_length=5, default="hi")
    description_translated = models.TextField(blank=True, help_text="Auto-translated to English")

    category = models.ForeignKey(
        Category, on_delete=models.SET_NULL, null=True, blank=True, related_name="complaints"
    )
    ai_category_confidence = models.FloatField(null=True, blank=True)

    # Status & workflow
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="submitted", db_index=True)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default="normal", db_index=True)
    urgency_score = models.FloatField(null=True, blank=True, help_text="AI-generated 0–1 urgency score")

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_complaints",
    )
    due_date = models.DateField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

    # Location
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    address = models.TextField(blank=True)
    ward = models.CharField(max_length=100, blank=True, db_index=True)
    city = models.CharField(max_length=100, blank=True, db_index=True)
    pincode = models.CharField(max_length=10, blank=True)

    # Meta
    source = models.CharField(max_length=15, choices=SOURCE_CHOICES, default="web")
    is_anonymous = models.BooleanField(default=False)
    is_duplicate = models.BooleanField(default=False)
    duplicate_of = models.ForeignKey(
        "self", on_delete=models.SET_NULL, null=True, blank=True, related_name="duplicates"
    )
    upvote_count = models.PositiveIntegerField(default=0)
    view_count = models.PositiveIntegerField(default=0)
    admin_notes = models.TextField(blank=True)

    # Phase 2 — clustering, NLP, community verification
    cluster_key = models.CharField(
        max_length=36,
        blank=True,
        db_index=True,
        help_text="Stable key grouping near-duplicate reports in the same area",
    )
    sentiment_score = models.FloatField(
        null=True,
        blank=True,
        help_text="Heuristic sentiment in [-1, 1] (negative civic stress → lower)",
    )
    extracted_locations = models.JSONField(
        default=_default_empty_list,
        blank=True,
        help_text="Phrases / pin codes extracted from description (speech NLP)",
    )
    verification_count = models.PositiveIntegerField(
        default=0,
        help_text="Distinct citizens who confirmed the on-ground issue",
    )

    class Meta:
        db_table = "complaints_complaint"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "city"]),
            models.Index(fields=["ward", "category"]),
        ]

    def __str__(self):
        return f"[{self.tracking_id}] {self.category} – {self.status}"

    def save(self, *args, **kwargs):
        if not self.tracking_id:
            self.tracking_id = self._generate_tracking_id()
        super().save(*args, **kwargs)

    @staticmethod
    def _generate_tracking_id() -> str:
        import random
        num = random.randint(10000000, 99999999)
        return f"NA-{num}"


class ComplaintStatusHistory(TimeStampedModel):
    """Immutable log of every status transition."""

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="status_history"
    )
    old_status = models.CharField(max_length=20, blank=True)
    new_status = models.CharField(max_length=20)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )
    note = models.TextField(blank=True)

    class Meta:
        db_table = "complaints_status_history"
        ordering = ["-created_at"]

    def __str__(self):
        return f"{self.complaint.tracking_id}: {self.old_status} → {self.new_status}"


class ComplaintAttachment(TimeStampedModel):
    """Photos or voice clips attached to a complaint."""

    FILE_TYPE_CHOICES = [("image", "Image"), ("audio", "Audio")]

    complaint = models.ForeignKey(
        Complaint, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(upload_to="complaints/attachments/%Y/%m/")
    file_type = models.CharField(max_length=10, choices=FILE_TYPE_CHOICES)
    original_filename = models.CharField(max_length=255, blank=True)
    file_size_bytes = models.PositiveBigIntegerField(null=True, blank=True)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
    )

    class Meta:
        db_table = "complaints_attachment"
        ordering = ["-created_at"]


class ComplaintUpvote(models.Model):
    """One upvote per user per complaint."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="upvotes")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_upvote"
        unique_together = ("complaint", "user")


class FAQEntry(TimeStampedModel):
    """Curated Q&A for the voice / text FAQ assistant."""

    question = models.CharField(max_length=255)
    keywords = models.TextField(
        blank=True,
        help_text="Comma-separated keywords to match user queries (case-insensitive)",
    )
    answer = models.TextField()
    is_active = models.BooleanField(default=True)
    sort_order = models.PositiveSmallIntegerField(default=0)

    class Meta:
        db_table = "complaints_faq_entry"
        ordering = ["sort_order", "id"]

    def __str__(self):
        return self.question[:60]


class IssueVerification(models.Model):
    """Community confirmation that a reported civic issue still exists on site."""

    complaint = models.ForeignKey(Complaint, on_delete=models.CASCADE, related_name="issue_verifications")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "complaints_issue_verification"
        unique_together = ("complaint", "user")
        indexes = [models.Index(fields=["complaint", "-created_at"])]
