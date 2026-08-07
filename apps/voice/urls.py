from django.urls import path
from . import views

urlpatterns = [
    path("transcribe/",        views.TranscribeView.as_view(),          name="voice-transcribe"),
    path("languages/",         views.SupportedLanguagesView.as_view(),  name="voice-languages"),
    path("jobs/",              views.VoiceJobListView.as_view(),        name="voice-job-list"),
    path("jobs/<uuid:pk>/",    views.VoiceJobDetailView.as_view(),      name="voice-job-detail"),
]
