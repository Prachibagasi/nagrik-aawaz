import io
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.voice.services.audio_utils import AudioValidationError, validate_audio_file


def test_accepts_ogg_with_empty_mime():
    """Some browsers send no or generic MIME; extension must still allow OGG."""
    f = SimpleUploadedFile("WhatsApp_test.ogg", b"OggS" + b"\x00" * 200, content_type="")
    validate_audio_file(f)


def test_accepts_ogg_with_octet_stream():
    f = SimpleUploadedFile("clip.ogg", b"x" * 500, content_type="application/octet-stream")
    validate_audio_file(f)


def test_rejects_bad_extension_with_empty_mime():
    f = SimpleUploadedFile("malware.exe", b"x" * 100, content_type="")
    with pytest.raises(AudioValidationError):
        validate_audio_file(f)


def test_rejects_oversize():
    big = io.BytesIO(b"x" * (26 * 1024 * 1024))
    big.name = "huge.wav"
    f = SimpleUploadedFile("huge.wav", big.getvalue(), content_type="audio/wav")
    with pytest.raises(AudioValidationError, match="too large"):
        validate_audio_file(f)
