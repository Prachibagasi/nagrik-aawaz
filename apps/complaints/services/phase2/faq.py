"""Keyword FAQ matcher — complaint status & tracking only; curated via Django admin."""
from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

from apps.complaints.models import FAQEntry

# (question, keywords_csv, answer) — keywords include English + Hindi for better matching.
DEFAULT_STATUS_FAQ_SEEDS: List[Tuple[str, str, str]] = [
    (
        "How do I track my complaint? / शिकायत की स्थिति कैसे देखें?",
        "track, tracking, ticket, id, ticket id, trace, follow, status, देख, पता, ट्रैक, स्थिति, शिकायत, कहाँ, कहा, खोज, number, नंबर",
        "Open the **Track** page on the website (or **Track** in the app), enter your **tracking ID** (ticket number), and press search — you will see the current **status** and history. "
        "वेबसाइट पर **Track** पेज खोलें, अपना **tracking ID** डालें और खोजें — वहाँ **status** और अपडेट दिखेंगे।",
    ),
    (
        "Where do I find my tracking ID?",
        "tracking id, ticket number, reference, forgot id, id kaha, आईडी, टिकट, नंबर, मिलेगा, कहाँ मिलेगा",
        "After you submit a complaint, the **tracking ID** is shown on the success screen and in **My complaints**. You can also open the complaint detail page — the ID is at the top. "
        "शिकायत भेजने के बाद **tracking ID** सफलता वाली स्क्रीन और **My complaints** में दिखता है; डिटेल पेज पर भी ऊपर लिखा होता है।",
    ),
    (
        "What do complaint statuses mean?",
        "status, stages, submitted, acknowledged, progress, resolved, rejected, meaning, मतलब, क्या होता, स्थिति",
        "**Submitted** — received. **Acknowledged** — department has seen it. **In progress** — work ongoing. **Resolved** — closed as fixed. **Rejected** — not taken up (reason may be noted). "
        "ये स्टेज्स टिकट पर दिखती हैं; अफसर बदलाव करते ही **Track** / **My complaints** में अपडेट हो जाता है।",
    ),
    (
        "How do I know if my complaint was received?",
        "received, submit ho gayi, गई, पहुँची, confirm, confirmation, सबमिट",
        "After submit you should see a **success message** with a **tracking ID**. The same ticket appears under **My complaints** when you are logged in. "
        "सबमिट के बाद **success** और **tracking ID** दिखना चाहिए; लॉग इन होने पर **My complaints** में भी टिकट दिखेगा।",
    ),
    (
        "Why is my complaint status not updating?",
        "not updating, stuck, same status, update nahi, अपडेट नहीं, रुका",
        "Status changes only when an **officer** updates the workflow. If it has been long, note your **tracking ID** and follow up through the official channel shown on the portal. "
        "स्टेटस तभी बदलता है जब **अफसर** सिस्टम में अपडेट करे; समय ज़्यादा लगे तो **tracking ID** सेव करके संपर्क करें।",
    ),
    (
        "Can I see status without logging in?",
        "without login, bina login, public, guest, बिना लॉगिन",
        "Yes — use the **Track** page with your **tracking ID** only (no login needed for basic status). To see **all** your tickets and full detail, log in and open **My complaints**. "
        "हाँ — **Track** पर सिर्फ **tracking ID** से देख सकते हैं; सारी शिकायतें **लॉग इन** कर **My complaints** में।",
    ),
    (
        "What is the difference between My complaints and Track?",
        "my complaints, track difference, अंतर, फर्क",
        "**My complaints** lists every ticket for your **logged-in** account. **Track** looks up **one** ticket by **tracking ID** (works for anyone with the ID). "
        "**My complaints** = आपकी सारी टिकटें (लॉग इन). **Track** = एक ID से तुरंत स्थिति।",
    ),
]

FALLBACK_NO_MATCH = {
    "question": "Complaint status — quick help",
    "answer": (
        "This assistant only answers **complaint status & tracking**. "
        "Use **Track** with your **tracking ID**, or log in → **My complaints** for full detail. "
        "यहाँ सिर्फ **शिकायत की स्थिति / ट्रैकिंग** की मदद मिलती है — **Track** पर ID डालें या **My complaints** खोलें।"
    ),
}


def _split_keywords(row: FAQEntry) -> List[str]:
    if not row.keywords:
        return []
    return [k.strip().lower() for k in re.split(r"[,;\n]+", row.keywords) if k.strip()]


def _query_tokens(query: str) -> List[str]:
    """Words from Latin + Devanagari (length ≥ 2)."""
    q = (query or "").strip().lower()
    return [t for t in re.findall(r"[\w\u0900-\u0dff]+", q, flags=re.UNICODE) if len(t) >= 2]


def match_faq(query: str, limit: int = 3) -> Dict[str, Any]:
    raw = (query or "").strip()
    q = raw.lower()
    if len(raw) < 2:
        return {"matches": [], "best_confidence": 0.0}

    qs = FAQEntry.objects.filter(is_active=True).order_by("sort_order", "id")
    scored: List[tuple[float, FAQEntry]] = []

    for row in qs:
        confidence = 0.0
        question_l = row.question.lower()
        keywords_l = " ".join(_split_keywords(row))

        if q in question_l:
            confidence += 0.55
        elif question_l in q:
            confidence += 0.45

        for kw in _split_keywords(row):
            if not kw:
                continue
            min_len = 2 if len(kw) <= 5 or re.search(r"[\u0900-\u0dff]", kw) else 3
            if len(kw) >= min_len and kw in q:
                confidence += 0.24

        haystack = f"{question_l} {keywords_l}"
        seen_tok = set()
        for tok in _query_tokens(raw):
            if tok in seen_tok:
                continue
            seen_tok.add(tok)
            if len(tok) >= 2 and tok in haystack:
                confidence += 0.14

        words = set(re.findall(r"\w{3,}", q))
        qw = set(re.findall(r"\w{3,}", question_l))
        if words & qw:
            confidence += 0.05 * len(words & qw)

        if confidence > 0:
            scored.append((min(1.0, confidence), row))

    scored.sort(key=lambda x: -x[0])
    top = scored[:limit]

    matches = [
        {
            "question": row.question,
            "answer": row.answer,
            "confidence": round(c, 3),
            "id": str(row.id),
        }
        for c, row in top
    ]
    best = matches[0]["confidence"] if matches else 0.0

    if not matches:
        matches = [
            {
                "question": FALLBACK_NO_MATCH["question"],
                "answer": FALLBACK_NO_MATCH["answer"],
                "confidence": 0.12,
                "id": "fallback-status",
            }
        ]
        best = 0.12

    return {"matches": matches, "best_confidence": best}


def seed_faqs_if_empty() -> Optional[int]:
    """Idempotent seed for fresh installs / CI — complaint status FAQs only."""
    if FAQEntry.objects.exists():
        return None
    for i, (qst, kw, ans) in enumerate(DEFAULT_STATUS_FAQ_SEEDS):
        FAQEntry.objects.create(question=qst, keywords=kw, answer=ans, sort_order=i)
    return len(DEFAULT_STATUS_FAQ_SEEDS)
