"""TextBlob sentiment with a small civic-language fallback lexicon."""
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


def score_details(text: str) -> tuple[float, str]:
    """Return polarity in [-1, 1] and the scoring method used."""
    if not text or len(text.strip()) < 4:
        return 0.0, "empty"
    t = text.lower()
    neg = sum(1 for w in NEGATIVE if w in t)
    pos = sum(1 for w in POSITIVE if w in t)
    lexicon = max(-1.0, min(1.0, (neg - pos) * 0.18))
    stress = 0.15 if "!!!" in text or re.search(r"[A-Z]{8,}", text) else 0.0

    try:
        from textblob import TextBlob

        polarity = float(TextBlob(text).sentiment.polarity)
        # TextBlob handles general English tone; the small civic lexicon retains
        # signals such as "leak" and romanized Hindi when English polarity is neutral.
        raw = (0.8 * polarity) + (0.2 * lexicon) + stress
        return max(-1.0, min(1.0, raw)), "textblob+lexicon"
    except Exception:
        return max(-1.0, min(1.0, lexicon + stress)), "lexicon_fallback"


def score_text(text: str) -> float:
    """Compatibility wrapper returning only the polarity score."""
    return score_details(text)[0]
