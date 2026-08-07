import django.contrib.auth.models
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.CreateModel(
            name="User",
            fields=[
                ("password", models.CharField(max_length=128, verbose_name="password")),
                ("last_login", models.DateTimeField(blank=True, null=True, verbose_name="last login")),
                ("is_superuser", models.BooleanField(default=False)),
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, max_length=15, unique=True)),
                ("email", models.EmailField(blank=True, max_length=254, null=True)),
                ("full_name", models.CharField(blank=True, max_length=150)),
                ("role", models.CharField(choices=[("citizen","Citizen"),("officer","Field Officer"),("admin","Admin")], default="citizen", max_length=10)),
                ("preferred_language", models.CharField(default="hi", max_length=5)),
                ("ward", models.CharField(blank=True, max_length=100)),
                ("department", models.CharField(blank=True, max_length=100)),
                ("avatar", models.ImageField(blank=True, null=True, upload_to="avatars/")),
                ("fcm_token", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("is_staff", models.BooleanField(default=False)),
                ("is_phone_verified", models.BooleanField(default=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("groups", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.group")),
                ("user_permissions", models.ManyToManyField(blank=True, related_name="user_set", related_query_name="user", to="auth.permission")),
            ],
            options={"db_table": "accounts_user", "ordering": ["-created_at"]},
            managers=[("objects", django.contrib.auth.models.BaseUserManager())],
        ),
        migrations.CreateModel(
            name="OTPVerification",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("phone", models.CharField(db_index=True, max_length=15)),
                ("otp", models.CharField(max_length=6)),
                ("is_used", models.BooleanField(default=False)),
                ("expires_at", models.DateTimeField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"db_table": "accounts_otp", "ordering": ["-created_at"]},
        ),
    ]
