"""
Whisper / Google STT integration.
Requires ``openai-whisper``. OGG/WebM/MP3 decoding uses FFmpeg: we prefer the binary
from ``imageio-ffmpeg`` so a system FFmpeg install is not required on Windows.
"""
import logging
import os
import warnings

from .audio_utils import preprocess_audio_for_whisper
from .whisper_ffmpeg import ensure_bundled_ffmpeg_for_whisper

logger = logging.getLogger(__name__)

_model_cache: dict = {}

# Short civic-complaint style hints (kept brief to avoid polluting the transcript).
INDIC_PROMPTS = {
    "hi": "नागरिक शिकायत।",
    "ta": "குடிமக்கள் புகார்.",
    "mr": "नागरीक तक्रार.",
    "te": "పౌరుల ఫిర్యాదు.",
    "bn": "নাগরিক অভিযোগ।",
    "gu": "નાગરિક ફરિયાદ.",
}

WHISPER_TRANSCRIBE_OPTS = {
    "temperature": 0,
    "condition_on_previous_text": False,
}

# Whisper often hallucinates these on silence/noise — reject only obvious junk.
_HALLUCINATION_PHRASES = (
    "thank you for watching",
    "thanks for watching",
    "subscribe to",
    "copyright",
    "mbc",
    "amara.org",
)


def _looks_like_arabic_script(text: str) -> bool:
    return any("\u0600" <= ch <= "\u06FF" for ch in (text or ""))


def _looks_like_cjk(text: str) -> bool:
    return any("\u4e00" <= ch <= "\u9fff" for ch in (text or ""))


def _script_ratio(text: str, start: int, end: int) -> float:
    letters = [c for c in (text or "") if c.isalpha() or ("\u0900" <= c <= "\u097F")]
    if not letters:
        return 0.0
    in_range = sum(1 for c in letters if start <= ord(c) <= end)
    return in_range / len(letters)


def _is_low_quality_transcript(text: str, lang: str | None, segments: list | None) -> bool:
    """
    Reject only obvious garbage. Real mic recordings often have lower confidence than
    synthetic TTS — do not block those.
    """
    cleaned = (text or "").strip()
    if len(cleaned) < 3:
        return True
    if _looks_like_cjk(text):
        return True
    low = cleaned.lower()
    if any(p in low for p in _HALLUCINATION_PHRASES):
        return True

    if lang in ("hi", "mr"):
        if _looks_like_arabic_script(text):
            return True
    if lang == "hi" and _script_ratio(text, 0x0B80, 0x0BFF) > 0.5:
        # Tamil script when user picked Hindi
        return True
    if lang == "ta" and _script_ratio(text, 0x0900, 0x097F) > 0.5:
        return True

    return False


def _resolve_whisper_language(user_lang: str | None, settings):
    """
    Prefer the language the user picked in the UI.
    Returns (whisper_lang, transcribe_kw, respect_user_lang).
    """
    supported = getattr(settings, "SUPPORTED_LANGUAGES", {})
    user_lang = (user_lang or "").strip() or None
    auto_lang = getattr(settings, "WHISPER_AUTO_LANGUAGE", False)

    if user_lang and user_lang in supported:
        whisper_lang = user_lang
        respect_user = True
    elif auto_lang:
        whisper_lang = None
        respect_user = False
    else:
        whisper_lang = user_lang
        respect_user = bool(user_lang)

    transcribe_kw = dict(WHISPER_TRANSCRIBE_OPTS)
    use_prompt = getattr(settings, "WHISPER_USE_INITIAL_PROMPT", False)
    if use_prompt and whisper_lang and whisper_lang in INDIC_PROMPTS:
        transcribe_kw["initial_prompt"] = INDIC_PROMPTS[whisper_lang]

    return whisper_lang, transcribe_kw, respect_user


def _get_whisper_model(model_size: str):
    if model_size not in _model_cache:
        import whisper

        _model_cache[model_size] = whisper.load_model(model_size)
    return _model_cache[model_size]


def _run_whisper(model, audio_path: str, language: str | None, extra_kw: dict):
    with warnings.catch_warnings():
        warnings.filterwarnings(
            "ignore",
            message="FP16 is not supported on CPU; using FP32 instead",
            category=UserWarning,
        )
        return model.transcribe(audio_path, language=language, **extra_kw)


def transcribe_audio(voice_job) -> dict:
    """
    Transcribe audio from a VoiceJob instance.
    Returns: { "transcript": str, "language": str, "confidence": float|None, optional flags }
    """
    try:
        from django.conf import settings

        provider = getattr(settings, "STT_PROVIDER", "whisper")

        if provider == "whisper":
            return _transcribe_whisper(voice_job)
        if provider == "google":
            return _transcribe_google(voice_job)
        raise ValueError(f"Unknown STT provider: {provider}")

    except Exception as exc:
        logger.exception("STT failed for job %s: %s", voice_job.id, exc)
        voice_job.status = "failed"
        voice_job.error_message = str(exc)
        voice_job.save(update_fields=["status", "error_message"])
        return {
            "transcript": "",
            "language": voice_job.language,
            "confidence": None,
            "stub_transcript": False,
            "transcription_failed": True,
        }


def _transcribe_whisper(voice_job) -> dict:
    """Whisper local inference. Install: pip install openai-whisper imageio-ffmpeg"""
    try:
        from django.conf import settings

        ensure_bundled_ffmpeg_for_whisper()
        import whisper  # noqa: F401 — ensure package exists
    except ImportError:
        logger.warning("openai-whisper not installed. Returning stub transcript.")
        voice_job.status = "done"
        voice_job.transcript = "[Whisper not installed – stub transcript]"
        voice_job.save(update_fields=["transcript", "status"])
        return {
            "transcript": voice_job.transcript,
            "language": voice_job.language,
            "confidence": None,
            "stub_transcript": True,
        }

    preprocessed_path = None
    try:
        voice_job.status = "processing"
        voice_job.save(update_fields=["status"])

        from django.conf import settings

        model_size = getattr(settings, "WHISPER_MODEL_SIZE", "small")
        model = _get_whisper_model(model_size)

        source_path = voice_job.audio_file.path
        try:
            preprocessed_path = preprocess_audio_for_whisper(source_path)
            audio_path = preprocessed_path
        except Exception as prep_exc:
            logger.warning("Audio preprocess failed, using original file: %s", prep_exc)
            audio_path = source_path

        user_lang = (voice_job.language or "").strip() or None
        whisper_lang, transcribe_kw, respect_user = _resolve_whisper_language(user_lang, settings)

        result = _run_whisper(model, audio_path, whisper_lang, transcribe_kw)
        transcript = result["text"].strip()
        segments = result.get("segments") or []
        detected = result.get("language")

        # Hindi → Urdu script: retry once.
        if respect_user and user_lang == "hi" and _looks_like_arabic_script(transcript):
            logger.info("Arabic script for Hindi job %s; retrying with language=hi", voice_job.id)
            retry_kw = dict(WHISPER_TRANSCRIBE_OPTS)
            result = _run_whisper(model, audio_path, "hi", retry_kw)
            transcript = result["text"].strip()
            segments = result.get("segments") or []
            detected = result.get("language") or "hi"

        # Still garbage: retry with small bump in temperature (sometimes helps short clips).
        check_lang = user_lang if respect_user else (detected or user_lang)
        if _is_low_quality_transcript(transcript, check_lang, segments):
            logger.info("Low-quality transcript for job %s; retrying with temperature fallback", voice_job.id)
            retry_kw = dict(transcribe_kw)
            retry_kw["temperature"] = (0.0, 0.2, 0.4)
            result = _run_whisper(model, audio_path, whisper_lang or check_lang, retry_kw)
            transcript = result["text"].strip()
            segments = result.get("segments") or []

        if _is_low_quality_transcript(transcript, check_lang, segments):
            voice_job.status = "failed"
            voice_job.transcript = ""
            voice_job.error_message = "low_quality_transcript"
            voice_job.save(update_fields=["status", "transcript", "error_message"])
            return {
                "transcript": "",
                "language": user_lang or voice_job.language,
                "confidence": None,
                "stub_transcript": False,
                "transcription_failed": True,
                "user_message": (
                    "Could not understand the recording. Speak for at least 3 seconds in a quiet room, "
                    "then try again — or type your complaint on the New complaint page."
                ),
            }

        voice_job.transcript = transcript
        if respect_user and user_lang:
            voice_job.language = user_lang
        else:
            voice_job.language = detected if detected else (user_lang or voice_job.language)
        voice_job.status = "done"
        voice_job.save(update_fields=["transcript", "language", "status"])

        return {
            "transcript": voice_job.transcript,
            "language": voice_job.language,
            "confidence": None,
            "stub_transcript": False,
        }

    except Exception as exc:
        logger.exception("Whisper inference failed for job %s", voice_job.id)
        err_text = str(exc)
        voice_job.status = "failed"
        voice_job.error_message = err_text[:2000]
        voice_job.transcript = ""
        voice_job.save(update_fields=["status", "error_message", "transcript"])

        friendly = "[Transcription failed — "
        low = err_text.lower()
        if "ffmpeg" in low or "did not find executable" in low or "cannot find the file" in low:
            friendly += "FFmpeg is often required for OGG/WebM/MP3. Install FFmpeg and add it to PATH, or upload WAV. "
        friendly += "See server logs for details.]"

        return {
            "transcript": friendly,
            "language": voice_job.language,
            "confidence": None,
            "stub_transcript": False,
            "transcription_failed": True,
        }
    finally:
        if preprocessed_path:
            try:
                os.unlink(preprocessed_path)
            except OSError:
                pass


def _transcribe_google(voice_job) -> dict:
    """Google Speech-to-Text. Install: pip install google-cloud-speech"""
    try:
        from google.cloud import speech

        voice_job.status = "processing"
        voice_job.save(update_fields=["status"])

        client = speech.SpeechClient()
        with open(voice_job.audio_file.path, "rb") as f:
            audio_content = f.read()

        audio = speech.RecognitionAudio(content=audio_content)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            language_code=voice_job.language or "hi-IN",
            enable_automatic_punctuation=True,
        )

        response = client.recognize(config=config, audio=audio)
        transcript = " ".join(r.alternatives[0].transcript for r in response.results)
        confidence = (
            response.results[0].alternatives[0].confidence if response.results else None
        )

        voice_job.transcript = transcript.strip()
        voice_job.confidence = confidence
        voice_job.status = "done"
        voice_job.save(update_fields=["transcript", "confidence", "status"])

        return {
            "transcript": transcript,
            "language": voice_job.language,
            "confidence": confidence,
            "stub_transcript": False,
        }

    except ImportError:
        logger.warning("google-cloud-speech not installed.")
        voice_job.status = "failed"
        voice_job.error_message = "google-cloud-speech not installed"
        voice_job.save(update_fields=["status", "error_message"])
        return {"transcript": "", "language": voice_job.language, "confidence": None, "stub_transcript": False}
