"""Phase 2 growth features: clustering, SLA prediction, auto-assignment, FAQ, sentiment, location NLP."""

from .clustering import compute_cluster_key, find_cluster_complaints
from .sla_prediction import predict_sla_full, sentiment_trend_series
from .auto_assignment import suggest_assignee, try_auto_assign
from .sentiment import score_text
from .location_nlp import extract_places
from .faq import match_faq, seed_faqs_if_empty
from .enrichment import enrich_complaint_after_classify

__all__ = [
    "compute_cluster_key",
    "find_cluster_complaints",
    "predict_sla_full",
    "sentiment_trend_series",
    "suggest_assignee",
    "try_auto_assign",
    "score_text",
    "extract_places",
    "match_faq",
    "seed_faqs_if_empty",
    "enrich_complaint_after_classify",
]
