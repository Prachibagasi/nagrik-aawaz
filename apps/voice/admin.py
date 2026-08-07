from django.contrib import admin
from .models import VoiceJob


@admin.register(VoiceJob)
class VoiceJobAdmin(admin.ModelAdmin):
    list_display = ("id", "submitted_by", "language", "status", "provider", "duration_seconds", "created_at")
    list_filter = ("status", "provider", "language")
    search_fields = ("submitted_by__phone", "transcript")
    readonly_fields = ("id", "transcript", "confidence", "status", "error_message", "created_at", "updated_at")
    ordering = ("-created_at",)
