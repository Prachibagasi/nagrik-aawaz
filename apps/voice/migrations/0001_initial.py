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
            name="VoiceJob",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("audio_file", models.FileField(upload_to="voice/jobs/%Y/%m/")),
                ("language", models.CharField(default="hi", max_length=5)),
                ("transcript", models.TextField(blank=True)),
                ("confidence", models.FloatField(blank=True, null=True)),
                ("provider", models.CharField(default="whisper", max_length=20)),
                ("status", models.CharField(choices=[("pending","Pending"),("processing","Processing"),("done","Done"),("failed","Failed")], default="pending", max_length=15)),
                ("error_message", models.TextField(blank=True)),
                ("duration_seconds", models.FloatField(blank=True, null=True)),
                ("complaint", models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="voice_job", to="complaints.complaint")),
                ("submitted_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "voice_job", "ordering": ["-created_at"]},
        ),
    ]
