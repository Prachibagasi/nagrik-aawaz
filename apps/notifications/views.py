from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated

from apps.core.permissions import IsAdmin
from .models import NotificationLog
from .serializers import NotificationLogSerializer, SendNotificationSerializer
from .services.delivery import deliver_notification


class NotificationListView(APIView):
    """GET /api/v1/notifications/ — user's own notifications."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        qs = NotificationLog.objects.filter(recipient=request.user)
        return Response(NotificationLogSerializer(qs, many=True).data)


class SendNotificationView(APIView):
    """POST /api/v1/notifications/send/ — admin-triggered manual notification."""

    permission_classes = [IsAuthenticated, IsAdmin]

    def post(self, request):
        serializer = SendNotificationSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        log = serializer.save()
        log = deliver_notification(log)
        return Response(NotificationLogSerializer(log).data)
