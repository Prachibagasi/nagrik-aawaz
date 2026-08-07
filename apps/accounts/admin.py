from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, OTPVerification


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    list_display = ("phone", "full_name", "role", "is_phone_verified", "is_active", "created_at")
    list_filter = ("role", "is_active", "is_phone_verified")
    search_fields = ("phone", "full_name", "email")
    ordering = ("-created_at",)

    fieldsets = (
        (None, {"fields": ("phone", "password")}),
        ("Personal info", {"fields": ("full_name", "email", "avatar", "preferred_language")}),
        ("Role & Assignment", {"fields": ("role", "ward", "department")}),
        ("Verification", {"fields": ("is_phone_verified", "fcm_token")}),
        ("Permissions", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions")}),
        ("Dates", {"fields": ("last_login",)}),
    )

    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("phone", "full_name", "role", "password1", "password2"),
        }),
    )


@admin.register(OTPVerification)
class OTPAdmin(admin.ModelAdmin):
    list_display = ("phone", "otp", "is_used", "expires_at", "created_at")
    list_filter = ("is_used",)
    search_fields = ("phone",)
    ordering = ("-created_at",)
