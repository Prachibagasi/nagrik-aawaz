from django.contrib.auth import get_user_model
from rest_framework import serializers

from .models import NotificationLog

User = get_user_model()


class NotificationLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = NotificationLog
        fields = [
            "id", "channel", "subject", "body",
            "status", "error_message", "provider_message_id",
            "created_at",
        ]


class SendNotificationSerializer(serializers.Serializer):
    recipient_phone = serializers.CharField()
    channel = serializers.ChoiceField(choices=NotificationLog.CHANNEL_CHOICES)
    subject = serializers.CharField(required=False, default="", allow_blank=True)
    body = serializers.CharField()
    complaint_id = serializers.UUIDField(required=False, allow_null=True)

    def validate_recipient_phone(self, value):
        if not User.objects.filter(phone=value).exists():
            raise serializers.ValidationError("No user registered with this phone number.")
        return value

    def create(self, validated_data):
        from apps.complaints.models import Complaint

        recipient = User.objects.get(phone=validated_data["recipient_phone"])
        complaint = None
        cid = validated_data.get("complaint_id")
        if cid:
            try:
                complaint = Complaint.objects.get(pk=cid)
            except Complaint.DoesNotExist as exc:
                raise serializers.ValidationError(
                    {"complaint_id": "Complaint not found."}
                ) from exc

        return NotificationLog.objects.create(
            recipient=recipient,
            complaint=complaint,
            channel=validated_data["channel"],
            subject=validated_data.get("subject", ""),
            body=validated_data["body"],
        )
