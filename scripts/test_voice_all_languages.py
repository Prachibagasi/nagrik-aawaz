#!/usr/bin/env python
"""
Generate short civic-complaint audio per language (edge-tts) and run Whisper STT.
Usage (from awaaz-backend, venv active):
  python scripts/test_voice_all_languages.py
"""
from __future__ import annotations

import asyncio
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
# Force small model for language tests (much better for Hindi/regional).
os.environ["WHISPER_MODEL_SIZE"] = "small"

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

import django  # noqa: E402

django.setup()

from django.conf import settings  # noqa: E402
from django.core.files import File  # noqa: E402

from apps.voice.models import VoiceJob  # noqa: E402
from apps.voice.services.stt_whisper import (  # noqa: E402
    _is_low_quality_transcript,
    transcribe_audio,
)

# Short complaint phrase per language (civic / water issue)
PHRASES: dict[str, str] = {
    "hi": "हमारे इलाके में दो दिन से पानी की आपूर्ति बंद है।",
    "en": "There is no water supply in our area for two days.",
    "ta": "எங்கள் பகுதியில் இரண்டு நாட்களாக தண்ணீர் வரவில்லை.",
    "mr": "आमच्या भागात दोन दिवसांपासून पाणीपुरवठा बंद आहे.",
}

EDGE_VOICES: dict[str, str] = {
    "hi": "hi-IN-SwaraNeural",
    "en": "en-IN-NeerjaNeural",
    "ta": "ta-IN-PallaviNeural",
    "mr": "mr-IN-AarohiNeural",
}


async def _synth_mp3(text: str, voice: str, out_path: str) -> None:
    import edge_tts

    comm = edge_tts.Communicate(text, voice)
    await comm.save(out_path)


def _script_hint(lang: str) -> tuple[int, int] | None:
    ranges = {
        "hi": (0x0900, 0x097F),
        "mr": (0x0900, 0x097F),
        "ta": (0x0B80, 0x0BFF),
        "te": (0x0C00, 0x0C7F),
        "bn": (0x0980, 0x09FF),
        "as": (0x0980, 0x09FF),
        "gu": (0x0A80, 0x0AFF),
        "kn": (0x0C80, 0x0CFF),
        "ml": (0x0D00, 0x0D7F),
        "pa": (0x0A00, 0x0A7F),
        "or": (0x0B00, 0x0B7F),
        "ur": (0x0600, 0x06FF),
    }
    return ranges.get(lang)


def _quality_ok(lang: str, phrase: str, transcript: str, failed: bool) -> bool:
    if failed or not transcript or transcript.startswith("["):
        return False
    if _is_low_quality_transcript(transcript, lang, None):
        return False
    if lang == "en":
        return any(w in transcript.lower() for w in ("water", "supply", "area", "days"))
    hint = _script_hint(lang)
    if hint:
        lo, hi = hint
        letters = [c for c in transcript if c.isalpha() or (lo <= ord(c) <= hi)]
        if not letters:
            return False
        in_script = sum(1 for c in letters if lo <= ord(c) <= hi)
        return in_script / len(letters) >= 0.3
    return len(transcript) > 5


def main() -> int:
    try:
        import edge_tts  # noqa: F401
    except ImportError:
        print("Install edge-tts first: pip install edge-tts")
        return 1

    langs = list(settings.SUPPORTED_LANGUAGES.keys())
    print(f"Whisper model: {settings.WHISPER_MODEL_SIZE}")
    print(f"Testing {len(langs)} languages...\n")
    print(f"{'Lang':<6} {'Name':<12} {'OK':<5} {'Transcript (preview)'}")
    print("-" * 90)

    passed = 0
    failed_langs: list[str] = []
    report_lines: list[str] = []

    for code in langs:
        name = settings.SUPPORTED_LANGUAGES[code]
        phrase = PHRASES.get(code, PHRASES["en"])
        voice = EDGE_VOICES.get(code)
        if not voice:
            print(f"{code:<6} {name:<12} SKIP  no edge-tts voice")
            continue

        with tempfile.TemporaryDirectory() as tmp:
            mp3 = os.path.join(tmp, f"test_{code}.mp3")
            try:
                asyncio.run(_synth_mp3(phrase, voice, mp3))
            except Exception as exc:
                print(f"{code:<6} {name:<12} FAIL  TTS error: {exc}")
                failed_langs.append(code)
                continue

            with open(mp3, "rb") as fh:
                job = VoiceJob(language=code, status="pending")
                job.audio_file.save(f"lang_test_{code}.mp3", File(fh), save=True)

            result = transcribe_audio(job)
            transcript = (result.get("transcript") or "").strip()
            tx_failed = bool(result.get("transcription_failed"))
            ok = _quality_ok(code, phrase, transcript, tx_failed)
            preview = transcript.replace("\n", " ")[:70]
            if ok:
                passed += 1
                mark = "PASS"
            else:
                failed_langs.append(code)
                mark = "FAIL"
            line = f"{code:<6} {name:<12} {mark:<5} {preview}"
            report_lines.append(f"{code}\t{name}\t{mark}\t{transcript}")
            try:
                print(line)
            except UnicodeEncodeError:
                print(f"{code:<6} {name:<12} {mark:<5} [unicode transcript — see report file]")

            job.delete()
            if job.audio_file:
                job.audio_file.delete(save=False)

    print("-" * 90)
    print(f"Result: {passed}/{len(langs)} passed")
    report_path = ROOT / "scripts" / "voice_language_test_report.txt"
    report_path.write_text(
        "code\tlanguage\tstatus\ttranscript\n" + "\n".join(report_lines),
        encoding="utf-8",
    )
    print(f"Full report: {report_path}")
    if failed_langs:
        print(f"Failed or low quality: {', '.join(failed_langs)}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
