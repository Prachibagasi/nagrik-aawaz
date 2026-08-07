import uuid
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("complaints", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("channel", models.CharField(choices=[("sms","SMS"),("push","Push Notification"),("email","Email"),("whatsapp","WhatsApp")], max_length=15)),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField()),
                ("status", models.CharField(choices=[("pending","Pending"),("sent","Sent"),("failed","Failed")], default="pending", max_length=10)),
                ("provider_message_id", models.CharField(blank=True, max_length=255)),
                ("error_message", models.TextField(blank=True)),
                ("recipient", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="notifications", to=settings.AUTH_USER_MODEL)),
                ("complaint", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="notifications", to="complaints.complaint")),
            ],
            options={"db_table": "notifications_log", "ordering": ["-created_at"]},
        ),
    ]
