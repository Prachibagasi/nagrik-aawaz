from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

from apps.core.views import HealthView, IVRInboundStubView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/v1/health/", HealthView.as_view(), name="health"),
    path("api/v1/integrations/ivr/inbound/", IVRInboundStubView.as_view(), name="ivr-inbound"),

    # API v1
    path("api/v1/auth/",          include("apps.accounts.urls")),
    path("api/v1/complaints/",    include("apps.complaints.urls")),
    path("api/v1/voice/",         include("apps.voice.urls")),
    path("api/v1/ai/",            include("apps.ai_ml.urls")),
    path("api/v1/departments/",   include("apps.departments.urls")),
    path("api/v1/notifications/", include("apps.notifications.urls")),
]

if settings.DEBUG:
    try:
        import debug_toolbar
        urlpatterns += [path("__debug__/", include(debug_toolbar.urls))]
    except ImportError:
        pass
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
