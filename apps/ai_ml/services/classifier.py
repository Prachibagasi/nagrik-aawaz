"""Shared complaint classifier used by the AI API and complaint creation."""

import logging
import re

from .agent1_classifier import classify_agent1
from .agent1_config import NAGRIK_CATEGORY_MAP

logger = logging.getLogger(__name__)

# Extra civic categories not represented by Agent1's department/subcategory labels.
EXTRA_CATEGORY_RULES = {
    "Stray Animals": ("stray dog", "street dog", "stray animal", "stray cat", "dog bite", "cattle", "cow", "monkey", "animal bite", "kutte"),
    "Public Safety": ("crime", "police", "theft", "violence", "harassment", "security", "robbery", "fire", "accident"),
    "Noise Pollution": ("noise", "loud", "sound", "music", "horn", "disturb"),
    "Drainage & Flooding": ("waterlog", "waterlogged", "overflow", "stagnant", "puddle", "nala", "barsat", "drain", "sewage"),
    "Sanitation & Waste": ("garbage", "waste", "trash", "dust bin", "dirty", "cleanliness", "kachra"),
    "Parks & Gardens": ("park", "garden", "tree", "grass", "bench", "playground", "swing", "lawn"),
}


def _extra_category(text: str) -> str | None:
    lowered = (text or "").lower()
    matches = {
        category: sum(
            1 for term in terms
            if re.search(rf"(?<!\w){re.escape(term)}(?!\w)", lowered)
        )
        for category, terms in EXTRA_CATEGORY_RULES.items()
    }
    matches = {category: score for category, score in matches.items() if score}
    return max(matches, key=matches.get) if matches else None


def classify_text(text: str, language: str = "en") -> dict:
    """Return the shared Agent1 classification and sentiment response.

    Naive Bayes supplies department/issue predictions for the API, the Agent1 panel,
    and automatic category assignment during complaint creation. High-precision
    department rules remain visible in ``classification_source``. Extra civic
    categories outside the Agent1 training taxonomy use their own explicit rules.
    """
    try:
        classification_text = text
        lang = (language or "en").strip().lower()
        ascii_ratio = sum(1 for char in (text or "") if ord(char) < 128) / max(len(text or ""), 1)
        translation_status = (
            "not_needed" if lang in {"en", "english"} or ascii_ratio > 0.85 else "unavailable"
        )
        if translation_status == "unavailable":
            try:
                from django.conf import settings

                if getattr(settings, "GROQ_API_KEY", ""):
                    from .agent1_translator import translate_to_english

                    translated = translate_to_english(text, language)
                    if translated and translated.strip() and translated.strip() != text.strip():
                        classification_text = translated
                        translation_status = "translated"
            except Exception as exc:
                logger.warning("Complaint translation unavailable for classification: %s", exc)

        result = classify_agent1(classification_text)
        category = NAGRIK_CATEGORY_MAP.get(result["department"], "Other")
        extra = _extra_category(text)
        if extra:
            category = extra
            source = "category_rules"
            confidence = result["confidence"]
            all_scores = {extra: round(float(confidence), 4)}
            # Keep the Agent1 route visible for diagnostics/department routing;
            # the civic category is an additional portal-facing override.
            department = result["department"]
            subcategory = result["subcategory"]
        else:
            source = result["classification_source"]
            confidence = result["confidence"]
            department = result["department"]
            subcategory = result["subcategory"]
            all_scores = {}
            for department_label, score in result["department_scores"].items():
                mapped = NAGRIK_CATEGORY_MAP.get(department_label, "Other")
                all_scores[mapped] = round(all_scores.get(mapped, 0.0) + score, 4)
            if not all_scores:
                all_scores = {category: confidence}

        priority = result["priority"].lower()
        return {
            "category": category,
            "department": department,
            "subcategory": subcategory,
            "confidence": round(float(confidence), 4),
            "all_scores": all_scores,
            "model_version": result["model_version"],
            "classification_source": source,
            "translation_status": translation_status,
            "sentiment_polarity": result["sentiment_polarity"],
            "sentiment_method": result["sentiment_method"],
            "urgency_score": result["urgency_score"],
            "suggested_priority": priority,
        }
    except Exception as exc:
        logger.exception("Agent1 classification failed; using Other fallback: %s", exc)
        return {
            "category": "Other",
            "department": "Other",
            "subcategory": "Other",
            "confidence": 0.0,
            "all_scores": {},
            "model_version": "agent1-error-fallback",
            "classification_source": "error_fallback",
            "translation_status": "unavailable",
            "sentiment_polarity": 0.0,
            "sentiment_method": "unavailable",
            "urgency_score": 0.35,
            "suggested_priority": "normal",
        }
