"""Lightweight sentiment / stress scoring — no external ML deps (prod-friendly baseline)."""
from __future__ import annotations

import re

# English + roman Hindi cues for civic frustration (extend via DB / admin later)
NEGATIVE = (
    "broken", "damage", "garbage", "smell", "accident", "unsafe", "dark", "leak",
    "overflow", "blocked", "dirty", "urgent", "dies", "injury", "fire", "flood",
    "tota", "kharab", "ganda", "bekar", "problem", "danger",
)
POSITIVE = (
    "fixed", "thanks", "resolved", "good", "clean", "thank", "dhanyavaad", "theek",
)


def score_text(text: str) -> float:
    """
    Returns float in [-1.0, 1.0]. Negative = distressed / urgent tone.
    Replace with transformer API in production if needed.
    """
    if not text or len(text.strip()) < 4:
        return 0.0
    t = text.lower()
    neg = sum(1 for w in NEGATIVE if w in t)
    pos = sum(1 for w in POSITIVE if w in t)
    # Exclamation / ALL CAPS stress
    stress = 0.0
    if "!!!" in text or re.search(r"[A-Z]{8,}", text):
        stress += 0.15
    raw = (neg - pos) * 0.18 + stress
    return max(-1.0, min(1.0, raw))
