"""JSON file storage for dummy department portal complaints."""

import json
import logging
from datetime import date
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

DEPT_PREFIX = {
    "bijli": "UPCL",
    "jal": "UJS",
    "pwd": "PWD",
    "shiksha": "DSE",
}


def data_dir() -> Path:
    raw = getattr(settings, "DEPARTMENT_DATA_DIR", "")
    if raw:
        p = Path(raw)
        if p.is_dir():
            return p
    # Default: sibling folder in monorepo
    return Path(settings.BASE_DIR).parent / "DUMMY WEBSITES" / "backend" / "data"


def _file_for(dept_key: str) -> Path:
    data_dir().mkdir(parents=True, exist_ok=True)
    return data_dir() / f"{dept_key}.json"


def load_complaints(dept_key: str) -> list:
    path = _file_for(dept_key)
    if not path.is_file():
        return []
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, list) else []
    except Exception as exc:
        logger.warning("Could not read %s: %s", path, exc)
        return []


def save_complaints(dept_key: str, items: list) -> None:
    path = _file_for(dept_key)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)


def next_id(dept_key: str) -> str:
    prefix = DEPT_PREFIX.get(dept_key, dept_key.upper())
    year = date.today().year
    existing = load_complaints(dept_key)
    seq = len(existing) + 1
    return f"{prefix}-{year}-{str(seq).zfill(5)}"


def normalize_incoming(dept_key: str, body: dict) -> dict:
    today = date.today().isoformat()
    base = {
        "status": "Pending",
        "filed": today,
        "date": today,
        "source": "nagrik-awaaz",
    }
    if dept_key == "bijli":
        return {
            **base,
            "id": body.get("id") or next_id(dept_key),
            "name": body.get("name") or body.get("consumerName") or "Citizen",
            "mobile": body.get("mobile", ""),
            "district": body.get("district", ""),
            "category": body.get("category") or body.get("complaintType") or body.get("type") or "Other",
            "description": body.get("description") or body.get("desc") or "",
            "accountNo": body.get("accountNo", ""),
            "email": body.get("email", ""),
            "location": body.get("location", ""),
            "nagrik_complaint_id": body.get("nagrik_complaint_id", ""),
        }
    if dept_key == "jal":
        return {
            **base,
            "id": body.get("id") or next_id(dept_key),
            "accountNo": body.get("accountNo", "N/A"),
            "name": body.get("name", "Citizen"),
            "mobile": body.get("mobile", ""),
            "zone": body.get("zone") or body.get("district", ""),
            "type": body.get("type") or body.get("category") or "Other Request",
            "description": body.get("description") or body.get("desc") or "",
            "nagrik_complaint_id": body.get("nagrik_complaint_id", ""),
        }
    if dept_key == "shiksha":
        return {
            **base,
            "id": body.get("id") or next_id(dept_key),
            "name": body.get("name", "Citizen"),
            "mobile": body.get("mobile", ""),
            "email": body.get("email", ""),
            "empid": body.get("empid", ""),
            "cat": body.get("category") or body.get("cat") or "Other",
            "dist": body.get("district") or body.get("dist") or "",
            "school": body.get("school", ""),
            "desc": body.get("description") or body.get("desc") or "",
            "nagrik_complaint_id": body.get("nagrik_complaint_id", ""),
        }
    # pwd default
    return {
        **base,
        "id": body.get("id") or next_id(dept_key),
        "name": body.get("name", "Citizen"),
        "mobile": body.get("mobile", ""),
        "district": body.get("district", ""),
        "category": body.get("category", "Other"),
        "location": body.get("location", ""),
        "desc": body.get("description") or body.get("desc") or "",
        "nagrik_complaint_id": body.get("nagrik_complaint_id", ""),
        "updated": today,
        "timeline": ["Filed"],
    }


def add_complaint(dept_key: str, body: dict) -> dict:
    item = normalize_incoming(dept_key, body)
    items = load_complaints(dept_key)
    items.insert(0, item)
    save_complaints(dept_key, items)
    return item
