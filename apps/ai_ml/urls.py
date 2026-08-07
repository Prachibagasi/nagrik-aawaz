from django.urls import path
from . import views

urlpatterns = [
    path("classify/", views.ClassifyTextView.as_view(), name="ai-classify"),
    path("translate/", views.TranslateTextView.as_view(), name="ai-translate"),
    path("process-complaint/", views.ProcessComplaintView.as_view(), name="ai-process-complaint"),
    path("faq/query/", views.FAQQueryView.as_view(), name="ai-faq-query"),
    path("extract-location/", views.ExtractLocationView.as_view(), name="ai-extract-location"),
]
