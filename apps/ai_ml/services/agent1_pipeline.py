"""End-to-end Agent1 complaint processing pipeline for the web API."""

import os
from datetime import datetime
from pathlib import Path

import pandas as pd
from django.conf import settings

from .agent1_classifier import classify_agent1
from .agent1_config import (
    AUTHORITY_DETAILS,
    NAGRIK_CATEGORY_MAP,
    build_form_payload,
    department_portal_config,
)
from .agent1_draft import generate_formal_draft
from .agent1_translator import translate_to_english


def _records_csv() -> Path:
    p = Path(settings.MEDIA_ROOT) / "agent1" / "agent1_records.csv"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def generate_complaint_id() -> str:
    today = datetime.now().strftime("%Y%m%d")
    prefix = f"COMP-{today}-"
    path = _records_csv()
    next_num = 1
    if path.is_file():
        try:
            df = pd.read_csv(path, on_bad_lines="skip")
            if not df.empty and "Complaint ID" in df.columns:
                next_num = len(df[df["Complaint ID"].astype(str).str.startswith(prefix, na=False)]) + 1
        except Exception:
            pass
    return f"{prefix}{str(next_num).zfill(4)}"


def _save_record(
    complaint_id: str,
    timestamp: str,
    department: str,
    subcategory: str,
    priority: str,
    authority: str,
    raw_text: str,
    english_text: str,
    user_language: str,
    draft_path: str | None,
):
    path = _records_csv()
    row = pd.DataFrame(
        [[
            complaint_id, timestamp, department, subcategory, priority, authority,
            raw_text, english_text, user_language, "Pending", draft_path or "",
        ]],
        columns=[
            "Complaint ID", "Timestamp", "Department", "Subcategory", "Priority",
            "Authority", "Raw Input", "English Translation", "User Language",
            "Status", "Draft Letter Path",
        ],
    )
    write_header = not path.is_file()
    row.to_csv(path, mode="a", header=write_header, index=False)


def process_complaint(
    raw_text: str,
    *,
    user_language: str = "hi",
    complainant_name: str = "",
    mobile: str = "",
    email: str = "",
    title: str = "",
    district: str = "",
    city: str = "",
    ward: str = "",
    address: str = "",
    pincode: str = "",
    location: str = "",
    save_draft: bool = True,
) -> dict:
    """
    Agent1 parity: translate → classify → draft → portal routing payload.
    """
    raw = (raw_text or "").strip()
    if len(raw) < 3:
        raise ValueError("Complaint text is too short.")

    english = translate_to_english(raw, user_language)
    classification = classify_agent1(english)
    department = classification["department"]
    subcategory = classification["subcategory"]
    priority = classification["priority"]
    authority = classification["authority"]

    complaint_id = generate_complaint_id()
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dist = district or city or location
    loc_parts = [p for p in [address, ward, city, pincode] if p and str(p).strip()]
    full_location = ", ".join(loc_parts) if loc_parts else (location or city or district or "")
    name = (complainant_name or "").strip() or "The Complainant"

    draft_letter, draft_path = generate_formal_draft(
        complaint_id,
        department,
        subcategory,
        priority,
        english,
        raw,
        user_language,
        timestamp=timestamp,
        title=title,
        location=full_location,
        complainant_name=name,
        save=save_draft,
    )

    _save_record(
        complaint_id, timestamp, department, subcategory, priority, authority,
        raw, english, user_language, draft_path,
    )

    portal_meta = department_portal_config(department)
    form_payload = build_form_payload(
        department,
        subcategory,
        english,
        complaint_id,
        complainant_name=name,
        mobile=mobile,
        email=email,
        district=dist,
        location=full_location,
    )

    nagrik_category = NAGRIK_CATEGORY_MAP.get(department, "Other")

    return {
        "complaint_id": complaint_id,
        "timestamp": timestamp,
        "raw_text": raw,
        "english_text": english,
        "user_language": user_language,
        "department": department,
        "subcategory": subcategory,
        "priority": priority,
        "authority": authority,
        "authority_details": AUTHORITY_DETAILS.get(department, AUTHORITY_DETAILS["Other"]),
        "draft_letter": draft_letter,
        "draft_path": draft_path,
        "nagrik_category": nagrik_category,
        "classification": classification,
        "portal": {
            **portal_meta,
            "form_payload": form_payload,
        },
        "groq_enabled": bool(getattr(settings, "GROQ_API_KEY", "") or os.getenv("GROQ_API_KEY")),
    }
