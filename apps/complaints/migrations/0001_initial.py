import django.db.models.deletion
import uuid
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="Category",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("name", models.CharField(max_length=100, unique=True)),
                ("slug", models.SlugField(unique=True)),
                ("icon", models.CharField(blank=True, max_length=50)),
                ("description", models.TextField(blank=True)),
                ("is_active", models.BooleanField(default=True)),
                ("default_sla_days", models.PositiveSmallIntegerField(default=7)),
                ("sort_order", models.PositiveSmallIntegerField(default=0)),
            ],
            options={"db_table": "complaints_category", "verbose_name_plural": "Categories", "ordering": ["sort_order","name"]},
        ),
        migrations.CreateModel(
            name="Complaint",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("tracking_id", models.CharField(db_index=True, editable=False, max_length=12, unique=True)),
                ("title", models.CharField(blank=True, max_length=255)),
                ("description", models.TextField()),
                ("description_language", models.CharField(default="hi", max_length=5)),
                ("description_translated", models.TextField(blank=True)),
                ("ai_category_confidence", models.FloatField(blank=True, null=True)),
                ("status", models.CharField(choices=[("submitted","Submitted"),("acknowledged","Acknowledged"),("in_progress","In Progress"),("resolved","Resolved"),("closed","Closed"),("rejected","Rejected")], db_index=True, default="submitted", max_length=20)),
                ("priority", models.CharField(choices=[("low","Low"),("normal","Normal"),("high","High"),("critical","Critical")], db_index=True, default="normal", max_length=10)),
                ("urgency_score", models.FloatField(blank=True, null=True)),
                ("due_date", models.DateField(blank=True, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                ("latitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("longitude", models.DecimalField(blank=True, decimal_places=6, max_digits=9, null=True)),
                ("address", models.TextField(blank=True)),
                ("ward", models.CharField(blank=True, db_index=True, max_length=100)),
                ("city", models.CharField(blank=True, db_index=True, max_length=100)),
                ("pincode", models.CharField(blank=True, max_length=10)),
                ("source", models.CharField(choices=[("web","Web App"),("mobile","Mobile App"),("whatsapp","WhatsApp"),("ivr","IVR / Phone Call"),("api","API")], default="web", max_length=15)),
                ("is_anonymous", models.BooleanField(default=False)),
                ("is_duplicate", models.BooleanField(default=False)),
                ("upvote_count", models.PositiveIntegerField(default=0)),
                ("view_count", models.PositiveIntegerField(default=0)),
                ("admin_notes", models.TextField(blank=True)),
                ("user", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="complaints", to=settings.AUTH_USER_MODEL)),
                ("category", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="complaints", to="complaints.category")),
                ("assigned_to", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="assigned_complaints", to=settings.AUTH_USER_MODEL)),
                ("duplicate_of", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="duplicates", to="complaints.complaint")),
            ],
            options={"db_table": "complaints_complaint", "ordering": ["-created_at"]},
        ),
        migrations.AddIndex(
            model_name="complaint",
            index=models.Index(fields=["status","city"], name="complaints__status_city_idx"),
        ),
        migrations.AddIndex(
            model_name="complaint",
            index=models.Index(fields=["ward","category"], name="complaints__ward_cat_idx"),
        ),
        migrations.CreateModel(
            name="ComplaintStatusHistory",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("old_status", models.CharField(blank=True, max_length=20)),
                ("new_status", models.CharField(max_length=20)),
                ("note", models.TextField(blank=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="status_history", to="complaints.complaint")),
                ("changed_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "complaints_status_history", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ComplaintAttachment",
            fields=[
                ("id", models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("file", models.FileField(upload_to="complaints/attachments/%Y/%m/")),
                ("file_type", models.CharField(choices=[("image","Image"),("audio","Audio")], max_length=10)),
                ("original_filename", models.CharField(blank=True, max_length=255)),
                ("file_size_bytes", models.PositiveBigIntegerField(blank=True, null=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="attachments", to="complaints.complaint")),
                ("uploaded_by", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "complaints_attachment", "ordering": ["-created_at"]},
        ),
        migrations.CreateModel(
            name="ComplaintUpvote",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("complaint", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="upvotes", to="complaints.complaint")),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={"db_table": "complaints_upvote", "unique_together": {("complaint","user")}},
        ),
    ]
