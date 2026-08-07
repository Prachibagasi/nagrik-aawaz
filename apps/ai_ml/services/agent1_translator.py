"""Translate citizen complaint text to English (Agent1 Groq parity + fallback)."""

from .agent1_groq import groq_chat


def translate_to_english(text: str, user_language: str = "hi") -> str:
    raw = (text or "").strip()
    if not raw:
        return ""

    # Already mostly English — skip LLM when ASCII-heavy
    ascii_ratio = sum(1 for c in raw if ord(c) < 128) / max(len(raw), 1)
    if ascii_ratio > 0.85 and user_language in ("en", "English"):
        return raw

    system = (
        "You are an expert translator specializing in Indian languages and dialects "
        "(Hindi, Hinglish, Tamil, Marathi, Kumaoni, Garhwali). "
        "Translate citizen complaints into clear, simple English. "
        "Return ONLY the English translation — no preamble or quotes."
    )
    translated = groq_chat(system, f"Translate this complaint to English:\n{raw}", temperature=0.1, max_tokens=300)
    if translated:
        return translated

    # Offline fallback: return original (classifier rules handle mixed text)
    return raw
