"""Extract location hints from raw speech / text (pincode, 'near X', common civic phrases)."""
from __future__ import annotations

import re
from typing import List


PINCODE_RE = re.compile(r"\b(\d{6})\b")
NEAR_RE = re.compile(r"\b(?:near|close to|beside|opposite|adjacent to)\s+([^,.;\n]{3,80})", re.I)


def extract_places(text: str) -> List[str]:
    if not text:
        return []
    out: List[str] = []
    for m in PINCODE_RE.finditer(text):
        out.append(f"PIN {m.group(1)}")
    for m in NEAR_RE.finditer(text):
        chunk = m.group(1).strip()
        if chunk:
            out.append(f"Near {chunk[:60]}")
    # Ward / block mentions
    ward_m = re.search(r"\b(?:ward|zone)\s*[:#\-]?\s*([\w\s]{2,40})", text, re.I)
    if ward_m:
        out.append(f"Ward ref: {ward_m.group(1).strip()[:40]}")
    # Dedupe preserve order
    seen = set()
    uniq = []
    for x in out:
        k = x.lower()
        if k not in seen:
            seen.add(k)
            uniq.append(x)
    return uniq[:12]
