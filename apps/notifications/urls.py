from django.urls import path
from . import views

urlpatterns = [
    path("",        views.NotificationListView.as_view(), name="notification-list"),
    path("send/",   views.SendNotificationView.as_view(), name="notification-send"),
]
