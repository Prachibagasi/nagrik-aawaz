from django.contrib import admin
from .models import (
    Category,
    Complaint,
    ComplaintStatusHistory,
    ComplaintAttachment,
    ComplaintUpvote,
    FAQEntry,
    IssueVerification,
)


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "default_sla_days", "is_active", "sort_order")
    list_editable = ("is_active", "sort_order", "default_sla_days")
    prepopulated_fields = {"slug": ("name",)}


class StatusHistoryInline(admin.TabularInline):
    model = ComplaintStatusHistory
    extra = 0
    readonly_fields = ("old_status", "new_status", "changed_by", "note", "created_at")
    can_delete = False


class AttachmentInline(admin.TabularInline):
    model = ComplaintAttachment
    extra = 0
    readonly_fields = ("file", "file_type", "original_filename", "file_size_bytes", "created_at")
    can_delete = False


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ("question", "is_active", "sort_order", "created_at")
    list_filter = ("is_active",)
    search_fields = ("question", "keywords", "answer")


@admin.register(IssueVerification)
class IssueVerificationAdmin(admin.ModelAdmin):
    list_display = ("complaint", "user", "created_at")
    search_fields = ("complaint__tracking_id", "user__phone")
    raw_id_fields = ("complaint", "user")


@admin.register(Complaint)
class ComplaintAdmin(admin.ModelAdmin):
    list_display = (
        "tracking_id", "category", "status", "priority",
        "city", "ward", "assigned_to", "created_at",
    )
    list_filter = ("status", "priority", "category", "source", "city")
    search_fields = ("tracking_id", "description", "address", "user__phone")
    ordering = ("-created_at",)
    readonly_fields = ("tracking_id", "created_at", "updated_at", "view_count", "upvote_count")
    inlines = [StatusHistoryInline, AttachmentInline]

    fieldsets = (
        ("Identity", {"fields": ("tracking_id", "user", "source", "is_anonymous")}),
        ("Content", {"fields": ("title", "description", "description_language", "description_translated", "category", "ai_category_confidence")}),
        ("Status & Priority", {"fields": ("status", "priority", "urgency_score", "assigned_to", "due_date", "resolved_at")}),
        ("Location", {"fields": ("latitude", "longitude", "address", "ward", "city", "pincode")}),
        (
            "Meta",
            {
                "fields": (
                    "is_duplicate",
                    "duplicate_of",
                    "upvote_count",
                    "view_count",
                    "verification_count",
                    "cluster_key",
                    "sentiment_score",
                    "extracted_locations",
                    "admin_notes",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )
