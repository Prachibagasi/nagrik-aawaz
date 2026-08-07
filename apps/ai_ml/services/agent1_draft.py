"""Formal government complaint draft letter (Agent1 Groq + template fallback)."""

from datetime import datetime
from pathlib import Path

from django.conf import settings

from .agent1_config import AUTHORITY_DETAILS
from .agent1_groq import groq_chat


def _fallback_draft(
    complaint_id: str,
    timestamp: str,
    department: str,
    subcategory: str,
    priority: str,
    auth_info: dict,
    english_text: str,
    *,
    title: str = "",
    location: str = "",
    complainant_name: str = "The Complainant",
) -> str:
    priority_line = (
        "We urge you to treat this matter with the HIGHEST PRIORITY and take IMMEDIATE action."
        if priority == "High"
        else "We request you to address this matter at your earliest convenience."
    )
    subject_detail = (title or "").strip() or subcategory
    location_line = f"\nLocation of issue: {location.strip()}\n" if (location or "").strip() else "\n"
    return f"""
{auth_info['designation']}
{auth_info['office']}
{auth_info['address']}

Date: {timestamp}
Complaint Reference No.: {complaint_id}

Subject: Formal Complaint Regarding {subject_detail} — {department} Department
         [Priority: {priority} | Issue type: {subcategory}]

Respected Sir/Madam,

I, {complainant_name}, hereby bring to your kind attention a grievance pertaining to
the {department} department, specifically classified under the issue type: {subcategory}.

The complainant has reported the following concern:
"{english_text}"
{location_line}
This issue has been causing significant inconvenience and hardship to the affected citizen(s).
The matter falls squarely within the jurisdiction of your office, and we therefore formally
request your immediate intervention for resolution.

{priority_line}

We kindly request that:
  1. This complaint be duly acknowledged within 3 working days.
  2. A field inspection or investigation be conducted promptly.
  3. The complainant be informed of the action taken and the expected resolution timeline.
  4. This complaint be tracked under reference number {complaint_id} for follow-up purposes.

Thanking you in anticipation of your prompt action.

Yours faithfully,

{complainant_name}
(On behalf of the Complainant)
Date: {timestamp}
Complaint ID: {complaint_id}
""".strip()


def generate_formal_draft(
    complaint_id: str,
    department: str,
    subcategory: str,
    priority: str,
    english_text: str,
    raw_text: str,
    user_language: str,
    *,
    timestamp: str | None = None,
    title: str = "",
    location: str = "",
    complainant_name: str = "",
    save: bool = True,
) -> tuple[str, str | None]:
    ts = timestamp or datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    auth_info = AUTHORITY_DETAILS.get(department, AUTHORITY_DETAILS["Other"])
    citizen = (complainant_name or "").strip() or "The Complainant"
    subject_hint = (title or "").strip() or subcategory

    system = (
        "You are an expert government correspondence writer for Uttarakhand, India. "
        "Write a formal complaint letter in English addressed to the authority provided. "
        "The letter MUST reflect the citizen's actual complaint text — do not invent a different issue. "
        "Use Subject, Salutation, numbered paragraphs, and 'Yours faithfully'. "
        "Include complaint ID, priority, issue location if provided, and the exact grievance described. "
        "Output ONLY the letter text."
    )
    user = (
        f"Complaint ID: {complaint_id}\n"
        f"Date & Time: {ts}\n"
        f"Complainant name: {citizen}\n"
        f"Department: {department}\n"
        f"Issue Category: {subcategory}\n"
        f"Subject line hint: {subject_hint}\n"
        f"Priority: {priority}\n"
        f"Location: {location or 'Not specified'}\n"
        f"Authority: {auth_info['designation']}, {auth_info['office']}\n"
        f"Address: {auth_info['address']}\n"
        f"Citizen language: {user_language}\n"
        f"Original complaint: {raw_text}\n"
        f"English translation: {english_text}\n"
        "Write the complete formal letter based on THIS complaint only."
    )

    draft = groq_chat(system, user, temperature=0.4, max_tokens=800)
    if not draft:
        draft = _fallback_draft(
            complaint_id,
            ts,
            department,
            subcategory,
            priority,
            auth_info,
            english_text,
            title=title,
            location=location,
            complainant_name=citizen,
        )

    saved_path = None
    if save:
        drafts_dir = Path(settings.MEDIA_ROOT) / "agent1" / "drafts"
        drafts_dir.mkdir(parents=True, exist_ok=True)
        path = drafts_dir / f"{complaint_id}.txt"
        path.write_text(draft, encoding="utf-8")
        saved_path = f"media/agent1/drafts/{complaint_id}.txt"

    return draft, saved_path
