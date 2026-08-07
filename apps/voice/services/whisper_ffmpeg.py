"""
Whisper's ``audio.load_audio`` shells out to an ``ffmpeg`` binary. On Windows many dev
machines do not have FFmpeg on PATH. ``imageio-ffmpeg`` ships a portable binary; we
patch ``whisper.audio.run`` once so decoding works for OGG/WebM/MP3 without a system install.
"""
from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_patched = False


def ensure_bundled_ffmpeg_for_whisper() -> None:
    """Idempotent: redirect whisper's ffmpeg subprocess to imageio-ffmpeg's binary."""
    global _patched
    if _patched:
        return
    try:
        import imageio_ffmpeg
        import whisper.audio as whisper_audio

        exe = imageio_ffmpeg.get_ffmpeg_exe()
        real_run = whisper_audio.run

        def run(cmd, *args, **kwargs):
            if isinstance(cmd, (list, tuple)) and cmd and cmd[0] == "ffmpeg":
                cmd = [exe] + list(cmd[1:])
            return real_run(cmd, *args, **kwargs)

        whisper_audio.run = run
        _patched = True
        logger.info("Whisper will use bundled FFmpeg: %s", exe)
    except Exception as exc:
        logger.debug("Bundled FFmpeg unavailable (install imageio-ffmpeg); using system PATH: %s", exc)
