from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from django.conf import settings
from django.utils import timezone
from rest_framework import serializers

from apps.accounts.serializers import UserSerializer
from .models import Category, Complaint, ComplaintStatusHistory, ComplaintAttachment

_COORD_STEP = Decimal("0.000001")


def quantize_lat_lng(value):
    """
    Match Complaint.latitude/longitude (max_digits=9, decimal_places=6).
    Browser GPS and JSON floats often exceed six fractional digits.
    """
    if value is None or value == "":
        return None
    try:
        return Decimal(str(value)).quantize(_COORD_STEP, rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError) as exc:
        raise serializers.ValidationError("Invalid coordinate.") from exc


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug", "icon", "description", "default_sla_days"]


class AttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = ComplaintAttachment
        fields = ["id", "file", "file_type", "original_filename", "file_size_bytes", "created_at"]
        read_only_fields = ["id", "created_at"]


class StatusHistorySerializer(serializers.ModelSerializer):
    changed_by_name = serializers.CharField(source="changed_by.full_name", read_only=True)

    class Meta:
        model = ComplaintStatusHistory
        fields = ["id", "old_status", "new_status", "changed_by_name", "note", "created_at"]


class ComplaintListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for list views."""

    category_name = serializers.CharField(source="category.name", read_only=True)
    user_name = serializers.CharField(source="user.full_name", read_only=True)

    class Meta:
        model = Complaint
        fields = [
            "id", "tracking_id", "title", "category_name", "status",
            "priority", "urgency_score", "city", "ward",
            "upvote_count", "source", "is_anonymous", "user_name",
            "cluster_key", "sentiment_score",
            "created_at", "updated_at",
        ]


class ComplaintDetailSerializer(serializers.ModelSerializer):
    """Full detail for single complaint retrieval."""

    category = CategorySerializer(read_only=True)
    attachments = AttachmentSerializer(many=True, read_only=True)
    status_history = StatusHistorySerializer(many=True, read_only=True)
    assigned_to = UserSerializer(read_only=True)
    cluster_neighbor_count = serializers.SerializerMethodField()
    user_id = serializers.SerializerMethodField()

    class Meta:
        model = Complaint
        fields = [
            "id", "tracking_id", "user_id",
            "description", "description_language", "description_translated",
            "title", "category", "ai_category_confidence",
            "status", "priority", "urgency_score",
            "latitude", "longitude", "address", "ward", "city", "pincode",
            "assigned_to", "due_date", "resolved_at",
            "upvote_count", "view_count", "verification_count",
            "source", "is_anonymous", "is_duplicate", "duplicate_of",
            "cluster_key", "sentiment_score", "extracted_locations",
            "cluster_neighbor_count",
            "admin_notes",
            "attachments", "status_history",
            "created_at", "updated_at",
        ]

    def get_cluster_neighbor_count(self, obj):
        if not obj.cluster_key:
            return 0
        return Complaint.objects.filter(cluster_key=obj.cluster_key).exclude(pk=obj.pk).count()

    def get_user_id(self, obj):
        return str(obj.user_id) if obj.user_id else None


class ComplaintCreateSerializer(serializers.ModelSerializer):
    # Accept full-precision GPS from JSON; model DecimalField(9,6) is enforced after quantize in validate_*.
    latitude = serializers.FloatField(required=False, allow_null=True)
    longitude = serializers.FloatField(required=False, allow_null=True)

    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.filter(is_active=True),
        source="category",
        required=False,
        allow_null=True,
    )
    attachments = serializers.ListField(
        child=serializers.FileField(),
        write_only=True,
        required=False,
    )

    class Meta:
        model = Complaint
        fields = [
            "description", "description_language",
            "title", "category_id",
            "latitude", "longitude", "address", "ward", "city", "pincode",
            "source", "is_anonymous",
            "attachments",
        ]

    def validate_description_language(self, value):
        supported = getattr(settings, "SUPPORTED_LANGUAGES", {})
        code = (value or "hi").strip()
        if supported and code not in supported:
            raise serializers.ValidationError(
                f"Unsupported language '{code}'. Choose from: {', '.join(supported)}"
            )
        return code

    def validate_latitude(self, value):
        return quantize_lat_lng(value)

    def validate_longitude(self, value):
        return quantize_lat_lng(value)

    def create(self, validated_data):
        from apps.ai_ml.services.classifier import classify_text

        attachment_files = validated_data.pop("attachments", [])
        user = self.context["request"].user if not validated_data.get("is_anonymous") else None
        complaint = Complaint.objects.create(user=user, **validated_data)

        for f in attachment_files:
            ct = f.content_type or ""
            ftype = "image" if ct.startswith("image") else "audio"
            ComplaintAttachment.objects.create(
                complaint=complaint,
                file=f,
                file_type=ftype,
                original_filename=f.name,
                file_size_bytes=f.size,
                uploaded_by=self.context["request"].user,
            )

        text = (complaint.description or "").strip()
        if text:
            result = classify_text(text, complaint.description_language or "hi")
            complaint.urgency_score = float(result.get("urgency_score") or 0)
            sp = result.get("suggested_priority")
            if sp in dict(Complaint.PRIORITY_CHOICES) and complaint.priority == "normal":
                complaint.priority = sp

            update_fields = ["urgency_score", "priority", "updated_at"]
            if complaint.category_id is None:
                name = result.get("category") or ""
                matched = Category.objects.filter(name=name, is_active=True).first()
                if matched:
                    complaint.category = matched
                    complaint.ai_category_confidence = float(result.get("confidence") or 0)
                    update_fields.extend(["category", "ai_category_confidence"])

            # Light “official language” stub for demo (translate service can replace later)
            if (complaint.description_language or "en") != "en":
                complaint.description_translated = f"[EN] {complaint.description}"
                update_fields.append("description_translated")

            complaint.save(update_fields=list(dict.fromkeys(update_fields)))

        from apps.complaints.services.phase2.enrichment import enrich_complaint_after_classify

        complaint.refresh_from_db()
        return enrich_complaint_after_classify(complaint)


class ComplaintStatusUpdateSerializer(serializers.Serializer):
    status = serializers.ChoiceField(choices=Complaint.STATUS_CHOICES)
    note = serializers.CharField(required=False, allow_blank=True, default="")
    priority = serializers.ChoiceField(choices=Complaint.PRIORITY_CHOICES, required=False)


class ComplaintAssignSerializer(serializers.Serializer):
    officer_id = serializers.UUIDField()
    due_date = serializers.DateField(required=False)
