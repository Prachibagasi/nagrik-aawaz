"""
Complaint text classification service.
Uses keyword rules as default fallback; plugs in sklearn/BERT when available.
Full ML model training in Module 6.
"""
import logging
import re

logger = logging.getLogger(__name__)

MODEL_VERSION = "v1-rules"

# Keyword-based urgency (demo / Phase-1; tone-based sentiment is future work)
URGENCY_CRITICAL = [
    "fire", "accident", "collapse", "electrocution", "electrocuted", "flood", "drowning",
    "emergency", "urgent", "gas leak", "explosion", "death", "injured", "blood",
]
URGENCY_HIGH = [
    "no water", "water supply", "unsafe", "theft", "robbery", "attack", "harassment",
    "broken wire", "live wire", "open manhole", "child", "school",
]


def urgency_from_text(text: str) -> tuple[float, str]:
    """
    Returns (urgency_score 0..1, suggested priority: low|normal|high|critical).
    """
    if not text or not text.strip():
        return 0.35, "normal"
    t = text.lower()
    if any(k in t for k in URGENCY_CRITICAL):
        return 0.92, "critical"
    if any(k in t for k in URGENCY_HIGH):
        return 0.72, "high"
    if len(t) > 200:
        return 0.55, "normal"
    return 0.45, "normal"


# Simple keyword rules for immediate use (expanded in Module 6 with real ML)
CATEGORY_KEYWORDS = {
    "Roads & Potholes": [
        "pothole", "road", "broken road", "sinkhole", "footpath", "sidewalk",
        "tarmac", "asphalt", "speed breaker", "divider", "sadak", "pothole",
    ],
    "Water Supply": [
        "water", "tap", "pipe", "leak", "no water", "drinking water",
        "supply", "pipeline", "borewell", "paani",
    ],
    "Sanitation & Waste": [
        "garbage", "waste", "trash", "dust bin", "sewage", "drain", "smell",
        "dirty", "cleanliness", "toilet", "sanitation", "kachra",
    ],
    "Electricity": [
        "light", "electricity", "power", "streetlight", "transformer",
        "wire", "electric", "bijli", "blackout", "outage",
    ],
    "Parks & Gardens": [
        "park", "garden", "tree", "grass", "bench", "playground", "swing",
        "maintenance", "lawn",
    ],
    "Public Safety": [
        "crime", "accident", "danger", "unsafe", "police", "theft", "fire",
        "violence", "harassment", "security",
    ],
    "Noise Pollution": [
        "noise", "loud", "sound", "music", "horn", "construction", "pollution",
        "disturb",
    ],
    "Drainage & Flooding": [
        "flood", "waterlog", "drain", "nala", "overflow", "stagnant", "puddle",
        "barsat", "rain",
    ],
    "Stray Animals": [
        "dog", "stray", "animal", "cattle", "cow", "monkey", "bite",
        "street dog", "kutte",
    ],
}


def classify_text(text: str, language: str = "en") -> dict:
    """
    Classify complaint text into a category.
    Returns: { "category": str, "confidence": float, "all_scores": dict, "model_version": str }
    """
    try:
        return _rule_based_classify(text)
    except Exception as exc:
        logger.exception("Classification failed: %s", exc)
        u_score, u_pri = urgency_from_text(text or "")
        return {
            "category": "Other",
            "confidence": 0.0,
            "all_scores": {},
            "model_version": MODEL_VERSION,
            "urgency_score": u_score,
            "suggested_priority": u_pri,
        }


def _rule_based_classify(text: str) -> dict:
    text_lower = text.lower()
    scores: dict[str, int] = {}

    for category, keywords in CATEGORY_KEYWORDS.items():
        count = sum(1 for kw in keywords if kw in text_lower)
        if count:
            scores[category] = count

    if not scores:
        u_score, u_pri = urgency_from_text(text)
        return {
            "category": "Other",
            "confidence": 0.5,
            "all_scores": {"Other": 1.0},
            "model_version": MODEL_VERSION,
            "urgency_score": u_score,
            "suggested_priority": u_pri,
        }

    total = sum(scores.values())
    normalized = {cat: round(cnt / total, 3) for cat, cnt in scores.items()}
    best_category = max(scores, key=scores.get)
    confidence = normalized[best_category]
    u_score, u_pri = urgency_from_text(text)

    return {
        "category": best_category,
        "confidence": confidence,
        "all_scores": normalized,
        "model_version": MODEL_VERSION,
        "urgency_score": u_score,
        "suggested_priority": u_pri,
    }
