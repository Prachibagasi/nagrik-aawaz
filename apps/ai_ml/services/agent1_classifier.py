"""Naive Bayes department and issue classification with explicit rule overrides."""

from __future__ import annotations

import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)

from .agent1_config import (  # noqa: E402
    AUTHORITY_MAP,
    BIJLI_TYPE_MAP,
    EDUCATION_CATEGORY_MAP,
    JAL_TYPE_MAP,
    PWD_CATEGORY_MAP,
)

_ml_ready = False
_vectorizer = None
_dept_model = None
_sub_models: dict[str, object] = {}
_ml_error: str | None = None


def _contains(text: str, *terms: str) -> bool:
    return any(re.search(rf"(?<!\w){re.escape(term.lower())}(?!\w)", text) for term in terms)


def _rule_department(text: str) -> str | None:
    """Use high-precision phrases for clear cases; defer ambiguous text to Naive Bayes."""
    t = (text or "").lower()

    if _contains(t, "electric", "electricity", "power cut", "power supply", "no power",
                 "no electricity", "electric meter", "electricity meter", "transformer", "voltage", "bijli", "outage",
                 "load shedding", "street light", "streetlight", "blackout"):
        return "Electricity"
    if _contains(t, "water logging", "waterlogged", "waterlogging", "stormwater drain",
                 "rainwater outlet", "rainwater drainage", "waste in open", "open dumping", "garbage", "sanitation"):
        return "PWD"
    if _contains(t, "road", "roads", "sadak", "rasta", "pothole", "potholes", "gaddha", "gaddhe",
                 "footpath", "highway", "bridge", "pathway", "road damage"):
        return "PWD"
    if _contains(t, "teacher", "teachers", "teacher's", "school", "exam", "scholarship", "mid-day meal",
                 "midday meal", "education", "student", "college", "textbook",
                 "admission", "classroom", "school bus", "salary", "salaries", "blackboard", "maps", "globes",
                 "internal marks", "study site", "study sites", "firewall", "school fee"):
        return "Education"
    if _contains(t, "bill", "billing", "tariff", "arrears", "penalty"):
        return "Water" if _contains(t, "water", "jal", "paani") else "Electricity"
    if _contains(t, "water", "water meter", "pipe", "tap", "sewage", "drain", "leakage", "leak",
                 "leaking", "flood", "borewell", "handpump", "tanker", "pipeline", "paani", "jal", "line burst"):
        return "Water"
    if _contains(t, "mobile network", "website", "web site", "portal", "login", "log in", "app keeps",
                 "complaint status", "verification code", "feedback form", "feature request", "status page"):
        return "Other"
    return None


def _rule_subcategory(dept: str, text: str) -> str | None:
    t = (text or "").lower()
    if dept == "Electricity":
        if _contains(t, "voltage", "dim", "surge", "low volt"):
            return "Voltage Issue"
        if _contains(t, "bill", "billing", "tariff", "arrears"):
            return "Wrong Bill"
        if _contains(t, "meter"):
            return "Meter Fault"
        if _contains(t, "street light", "streetlight", "street lamp"):
            return "Street Light Issue"
        if _contains(t, "no power", "no electricity", "blackout", "power cut", "transformer"):
            return "No Power Supply"
    elif dept == "Water":
        if _contains(t, "leak", "leaks", "leaking", "leakage", "burst", "broken pipe"):
            return "Pipe Leakage / Burst"
        if _contains(t, "sewage", "drain", "sewer"):
            return "Sewage / Drainage Problem"
        if _contains(t, "water quality", "dirty water", "contaminated", "smell"):
            return "Water Quality Issue"
        if _contains(t, "low pressure", "weak pressure"):
            return "Low Water Pressure"
        if _contains(t, "meter"):
            return "Meter Issue"
        if _contains(t, "connection"):
            return "New Water Connection"
        if _contains(t, "bill", "billing", "tariff", "arrears"):
            return "Billing Dispute"
        if _contains(t, "no water", "water supply", "supply stopped", "no supply"):
            return "Water Supply Disruption"
    elif dept == "PWD":
        if _contains(t, "bridge"):
            return "Bridge Condition"
        if _contains(t, "water logging", "waterlogging", "waterlogged", "drainage", "drain", "flooded road",
                     "stormwater", "rainwater outlet", "rainwater drainage"):
            return "Drainage / Waterlogging"
        if _contains(t, "encroach", "blocked footpath"):
            return "Encroachment on Road"
        if _contains(t, "streetlight", "street light", "road marking", "lane marking"):
            return "Streetlight / Road Marking"
        if _contains(t, "corruption", "bribery", "bribe", "kickback"):
            return "Corruption / Bribery"
        if _contains(t, "contractor", "poor construction", "construction quality"):
            return "Contractor Negligence"
        if _contains(t, "illegal road cutting", "road cutting", "road excavation", "road dug"):
            return "Illegal Road Cutting"
        if _contains(t, "garbage", "sanitation", "waste", "dump"):
            return "Garbage / Sanitation Issue"
        if _contains(t, "government building", "public building"):
            return "Government Building Issue"
        if _contains(t, "pothole", "potholes", "gaddha", "gaddhe", "sinkhole"):
            return "Road Damage / Pothole"
        if _contains(t, "broken", "damaged", "cracked") and _contains(t, "road", "roads", "sadak", "rasta", "path"):
            return "Road Damage / Pothole"
    elif dept == "Education":
        if _contains(t, "mid-day meal", "midday meal", "meal"):
            return "Mid-Day Meal Complaint"
        if _contains(t, "scholarship", "fee"):
            return "Scholarship / Fee Issue"
        if _contains(t, "exam", "examination", "result"):
            return "Examination Related"
        if _contains(t, "admission", "enrolment", "enrollment"):
            return "Admission Problem"
        if _contains(t, "salary", "pay dispute", "teacher pay"):
            return "Salary / Pay Dispute"
        if _contains(t, "blackboard", "classroom", "school building", "broken windows"):
            return "School Infrastructure Problem"
        if _contains(t, "maps", "globes", "textbook", "text book", "books", "school material"):
            return "Text Book / Material Unavailability"
        if _contains(t, "teacher transfer", "teacher posting"):
            return "Teacher Transfer / Posting Issue"
        if _contains(t, "internet", "wifi", "wi-fi", "tablet", "digital device", "firewall", "study site"):
            return "Digital Device / Internet Issue"
        if _contains(t, "teacher misconduct", "teacher misbehav", "teacher absent"):
            return "Teacher Misconduct"
        if _contains(t, "rti"):
            return "RTI Related"
        if _contains(t, "building", "infrastructure", "toilet", "classroom", "broken"):
            return "School Infrastructure Problem"
    return None


def _balanced_weights(labels):
    counts = labels.value_counts()
    class_count = len(counts)
    return labels.map(lambda label: len(labels) / (class_count * counts[label])).to_numpy()


def _load_ml() -> bool:
    """Train the in-process Naive Bayes models once from the configured CSV."""
    global _ml_ready, _vectorizer, _dept_model, _sub_models, _ml_error
    if _ml_ready:
        return True
    try:
        import pandas as pd
        from django.conf import settings
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.naive_bayes import MultinomialNB

        path = Path(getattr(settings, "AGENT1_TRAINING_DATA", ""))
        if not path.is_file():
            path = Path(__file__).resolve().parent.parent / "data" / "agent1_training.csv"
        df = pd.read_csv(path)
        required = {"text", "department", "subcategory"}
        missing = required.difference(df.columns)
        if missing:
            raise ValueError(f"Training CSV is missing columns: {', '.join(sorted(missing))}")
        df = df.dropna(subset=list(required)).copy()
        for col in required:
            df[col] = df[col].astype(str).str.strip()
        df = df[df["text"].ne("")]
        df = df.reset_index(drop=True)
        if df.empty or df["department"].nunique() < 2:
            raise ValueError("Training CSV needs non-empty text from at least two departments.")

        vectorizer = TfidfVectorizer(
            lowercase=True,
            strip_accents="unicode",
            analyzer="char_wb",
            ngram_range=(3, 5),
            sublinear_tf=True,
        )
        matrix = vectorizer.fit_transform(df["text"])
        dept_labels = df["department"]
        dept_model = MultinomialNB(alpha=0.2)
        dept_model.fit(matrix, dept_labels)

        sub_models = {}
        for department, rows in df.groupby("department"):
            labels = rows["subcategory"]
            model = MultinomialNB(alpha=0.2)
            model.fit(
                matrix[rows.index],
                labels,
                sample_weight=_balanced_weights(labels),
            )
            sub_models[department] = model

        _vectorizer = vectorizer
        _dept_model = dept_model
        _sub_models = sub_models
        _ml_error = None
        _ml_ready = True
        logger.info("Agent1 Naive Bayes models loaded from %s (%d examples)", path, len(df))
        return True
    except Exception as exc:
        _ml_error = str(exc)
        logger.exception("Agent1 Naive Bayes unavailable; using rule fallback: %s", exc)
        return False


def _predict(model, matrix) -> tuple[str | None, float, dict[str, float]]:
    if model is None or matrix.nnz == 0:
        return None, 0.0, {}
    probabilities = model.predict_proba(matrix)[0]
    scores = {str(label): float(prob) for label, prob in zip(model.classes_, probabilities)}
    label = max(scores, key=scores.get)
    return label, scores[label], scores


def _sentiment(text: str) -> tuple[float, str]:
    try:
        from apps.complaints.services.phase2.sentiment import score_details

        return score_details(text)
    except Exception as exc:
        logger.warning("TextBlob sentiment unavailable; using neutral score: %s", exc)
        return 0.0, "unavailable"


def _priority(text: str, polarity: float) -> tuple[str, float]:
    t = (text or "").lower()
    if _contains(t, "electrocution", "electrocuted", "live wire", "gas leak", "explosion",
                 "collapse", "drowning", "fire", "death", "fatal accident"):
        return "Critical", 0.96
    if _contains(t, "urgent", "emergency", "immediately", "asap", "no water", "no power",
                 "no electricity", "unsafe", "danger", "accident", "injured", "injury", "child",
                 "children", "fell", "days", "weeks", "months"):
        return "High", 0.78
    if polarity <= -0.4:
        return "High", 0.72
    if polarity < -0.05:
        return "Normal", 0.55
    return "Low", 0.35


def classify_agent1(english_text: str) -> dict:
    """Return department, issue type, NB scores, TextBlob sentiment and priority."""
    text = (english_text or "").strip()
    if not text:
        return {
            "department": "Other", "subcategory": "Other", "priority": "Low",
            "authority": AUTHORITY_MAP["Other"], "confidence": 0.0,
            "subcategory_confidence": 0.0, "department_scores": {},
            "sentiment_polarity": 0.0, "sentiment_method": "textblob",
            "urgency_score": 0.35, "classification_source": "empty",
            "model_version": "agent1-empty-v2",
        }

    polarity, sentiment_method = _sentiment(text)
    priority, urgency_score = _priority(text, polarity)
    ml_loaded = _load_ml()
    rule_dept = _rule_department(text)

    ml_dept = None
    ml_confidence = 0.0
    dept_scores: dict[str, float] = {}
    subcategory = None
    subcategory_confidence = 0.0
    if ml_loaded:
        matrix = _vectorizer.transform([text])
        ml_dept, ml_confidence, dept_scores = _predict(_dept_model, matrix)
        department = rule_dept or ml_dept or "Other"
        subcategory = _rule_subcategory(department, text)
        if subcategory is None:
            sub_model = _sub_models.get(department)
            subcategory, subcategory_confidence, _ = _predict(sub_model, matrix)
        source = "rules" if rule_dept else ("naive_bayes" if ml_dept else "unknown_text_fallback")
        model_version = "agent1-multinomial-nb-v3-char"
    else:
        department = rule_dept or "Other"
        subcategory = _rule_subcategory(department, text)
        source = "rules_fallback"
        model_version = "agent1-rules-v2"

    valid_subcategories = {
        "Electricity": set(BIJLI_TYPE_MAP) | set(BIJLI_TYPE_MAP.values()),
        "Water": set(JAL_TYPE_MAP) | set(JAL_TYPE_MAP.values()),
        "PWD": set(PWD_CATEGORY_MAP) | set(PWD_CATEGORY_MAP.values()),
        "Education": set(EDUCATION_CATEGORY_MAP) | set(EDUCATION_CATEGORY_MAP.values()),
        "Other": {"Other", "Other Request"},
    }.get(department, {"Other", "Other Request"})
    if subcategory not in valid_subcategories:
        subcategory = None
    if subcategory is None and ml_loaded:
        subcategory, subcategory_confidence, _ = _predict(_sub_models.get(department), _vectorizer.transform([text]))
        if subcategory not in valid_subcategories:
            subcategory = None
    if subcategory is None:
        subcategory = {
            "Electricity": "No Power Supply",
            "Water": "Water Supply Disruption",
            "PWD": "Road Damage / Pothole",
            "Education": "School Infrastructure Problem",
        }.get(department, "Other")

    return {
        "department": department,
        "subcategory": subcategory,
        "priority": priority,
        "urgency_score": urgency_score,
        "sentiment_polarity": round(polarity, 4),
        "sentiment_method": sentiment_method,
        "authority": AUTHORITY_MAP.get(department, AUTHORITY_MAP["Other"]),
        "confidence": round(dept_scores.get(department, ml_confidence), 4),
        "subcategory_confidence": round(subcategory_confidence, 4),
        "department_scores": {k: round(v, 4) for k, v in dept_scores.items()},
        "classification_source": source,
        "model_version": model_version,
        "model_error": _ml_error if not ml_loaded else None,
    }
