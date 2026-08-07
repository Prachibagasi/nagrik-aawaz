# Generated manually — replace FAQ rows with complaint-status-only content + Hindi keywords.

from django.db import migrations


def forwards(apps, schema_editor):
    FAQEntry = apps.get_model("complaints", "FAQEntry")
    FAQEntry.objects.all().delete()
    from apps.complaints.services.phase2.faq import DEFAULT_STATUS_FAQ_SEEDS

    for i, (question, keywords, answer) in enumerate(DEFAULT_STATUS_FAQ_SEEDS):
        FAQEntry.objects.create(
            question=question[:255],
            keywords=keywords,
            answer=answer,
            sort_order=i,
            is_active=True,
        )


def backwards(apps, schema_editor):
    FAQEntry = apps.get_model("complaints", "FAQEntry")
    FAQEntry.objects.all().delete()


class Migration(migrations.Migration):

    dependencies = [
        ("complaints", "0003_phase2_growth"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
