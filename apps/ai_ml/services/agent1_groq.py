"""Optional Groq LLM client (Agent1 parity). Uses GROQ_API_KEY from environment."""

import logging
import os

from django.conf import settings

logger = logging.getLogger(__name__)

GROQ_MODEL = getattr(settings, "GROQ_MODEL", "llama-3.3-70b-versatile")


def groq_api_key() -> str:
    return (
        getattr(settings, "GROQ_API_KEY", "")
        or os.getenv("GROQ_API_KEY", "")
        or ""
    ).strip()


def groq_available() -> bool:
    return bool(groq_api_key())


def groq_chat(system: str, user: str, *, temperature: float = 0.2, max_tokens: int = 800) -> str | None:
    if not groq_available():
        return None
    try:
        from groq import Groq

        client = Groq(api_key=groq_api_key())
        response = client.chat.completions.create(
            model=GROQ_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        return (response.choices[0].message.content or "").strip()
    except Exception as exc:
        logger.warning("Groq request failed: %s", exc)
        return None
