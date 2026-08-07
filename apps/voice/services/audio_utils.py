"""Audio file validation and metadata extraction."""
import logging
import os
import subprocess
import tempfile

from django.conf import settings

logger = logging.getLogger(__name__)

ALLOWED_MIME_TYPES = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/ogg",
    "audio/x-ogg",
    "application/ogg",
    "audio/opus",
    "audio/webm",
    "audio/mp4",
    "audio/m4a",
    "audio/aac",
    "audio/flac",
    "application/octet-stream",
}
ALLOWED_EXTENSIONS = (".mp3", ".wav", ".ogg", ".webm", ".m4a", ".aac", ".flac")
MAX_BYTES = getattr(settings, "MAX_VOICE_FILE_SIZE_MB", 25) * 1024 * 1024


class AudioValidationError(Exception):
    pass


def validate_audio_file(file):
    """Raise AudioValidationError if the file is not a valid audio upload."""
    if file.size > MAX_BYTES:
        raise AudioValidationError(
            f"Audio file too large. Max allowed: {MAX_BYTES // (1024*1024)} MB."
        )
    name = getattr(file, "name", "") or ""
    ext = os.path.splitext(name)[1].lower()
    raw_ct = getattr(file, "content_type", "") or ""
    content_type = raw_ct.split(";")[0].strip().lower()

    # Browsers often omit MIME for some recordings; trust extension as fallback.
    if content_type:
        if content_type in ALLOWED_MIME_TYPES:
            return
        if ext in ALLOWED_EXTENSIONS:
            return
        raise AudioValidationError(
            f"Unsupported audio format: {content_type or ext} (file: {name})."
        )

    if ext in ALLOWED_EXTENSIONS:
        return

    raise AudioValidationError(
        f"Unsupported audio file extension {ext or '(none)'}. Allowed: {', '.join(ALLOWED_EXTENSIONS)}."
    )


def get_audio_duration(file_path: str) -> float | None:
    """Return duration in seconds using mutagen or ffprobe; None if unavailable."""
    try:
        from mutagen import File as MutagenFile
        audio = MutagenFile(file_path)
        if audio and audio.info:
            return round(audio.info.length, 2)
    except ImportError:
        pass
    except Exception as exc:
        logger.debug("mutagen duration check failed: %s", exc)

    try:
        import subprocess
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "default=noprint_wrappers=1:nokey=1", file_path],
            capture_output=True, text=True, timeout=10,
        )
        if result.returncode == 0 and result.stdout.strip():
            return round(float(result.stdout.strip()), 2)
    except Exception:
        pass

    return None


def preprocess_audio_for_whisper(input_path: str) -> str:
    """
    Convert any upload/recording to 16 kHz mono PCM WAV — Whisper is more accurate on this
    than raw browser WebM/OGG.
    Returns path to a temp file the caller must delete.
    """
    try:
        import imageio_ffmpeg

        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError as exc:
        raise RuntimeError("imageio-ffmpeg is required for voice preprocessing") from exc

    out = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    out.close()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        input_path,
        "-ar",
        "16000",
        "-ac",
        "1",
        "-c:a",
        "pcm_s16le",
        out.name,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
    if result.returncode != 0:
        try:
            os.unlink(out.name)
        except OSError:
            pass
        err = (result.stderr or result.stdout or "ffmpeg failed")[:500]
        raise RuntimeError(f"Audio conversion failed: {err}")
    return out.name
