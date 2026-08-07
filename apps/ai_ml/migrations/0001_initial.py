import uuid
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True
    dependencies = [
        ("complaints", "0001_initial"),
    ]
    operations = [
        migrations.CreateModel(
            name="ClassificationResult",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("input_text", models.TextField()),
                ("predicted_category", models.CharField(max_length=100)),
                ("confidence", models.FloatField()),
                ("all_scores", models.JSONField(default=dict)),
                ("model_version", models.CharField(default="v1", max_length=50)),
                ("accepted", models.BooleanField(blank=True, null=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="classifications", to="complaints.complaint")),
            ],
            options={"db_table": "ai_ml_classification", "ordering": ["-created_at"]},
        ),
    ]
