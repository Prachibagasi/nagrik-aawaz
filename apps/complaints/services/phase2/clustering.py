"""Duplicate-style clustering: stable keys from normalized text + geography."""
from __future__ import annotations

import hashlib
import re

from django.db.models import QuerySet

from apps.complaints.models import Complaint


def normalize_snippet(text: str, max_len: int = 120) -> str:
    if not text:
        return ""
    s = text.lower().strip()
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"[^\w\s\u0900-\u0fff]", " ", s)  # keep alnum + Indic blocks
    s = re.sub(r"\s+", " ", s).strip()
    return s[:max_len]


def compute_cluster_key(description: str, city: str = "", ward: str = "") -> str:
    """
    Deterministic key: same area + similar opening text → same cluster bucket.
    Not a full ML duplicate detector; production systems would add embeddings.
    """
    base = normalize_snippet(description or "", 200)
    if len(base) < 12:
        return ""
    seed = base[:72]
    city_part = (city or "").strip().lower()[:50]
    ward_part = (ward or "").strip().lower()[:50]
    raw = f"{seed}|{city_part}|{ward_part}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def find_cluster_complaints(cluster_key: str, exclude_pk=None) -> QuerySet:
    if not cluster_key:
        return Complaint.objects.none()
    qs = Complaint.objects.filter(cluster_key=cluster_key).order_by("-created_at")
    if exclude_pk:
        qs = qs.exclude(pk=exclude_pk)
    return qs
