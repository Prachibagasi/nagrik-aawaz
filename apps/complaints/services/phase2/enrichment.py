"""Post-create enrichment for Phase 2 fields & optional auto-assignment."""
from __future__ import annotations

from django.db import transaction

from apps.complaints.models import Complaint

from .auto_assignment import try_auto_assign
from .clustering import compute_cluster_key
from .location_nlp import extract_places
from .sentiment import score_text


def enrich_complaint_after_classify(complaint: Complaint) -> Complaint:
    """Called after AI classify block has saved category / urgency."""
    text = (complaint.description or "").strip()

    update_fields: list[str] = []

    if text:
        complaint.sentiment_score = score_text(text)
        update_fields.append("sentiment_score")
        complaint.extracted_locations = extract_places(text)
        update_fields.append("extracted_locations")

    ck = compute_cluster_key(
        complaint.description,
        complaint.city or "",
        complaint.ward or "",
    )
    if ck:
        complaint.cluster_key = ck
        update_fields.append("cluster_key")

    if update_fields:
        complaint.save(update_fields=list(dict.fromkeys(update_fields)))

    with transaction.atomic():
        complaint.refresh_from_db()
        try_auto_assign(complaint)

    return complaint
