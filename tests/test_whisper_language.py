import pytest
from django.test import override_settings

from apps.voice.services.stt_whisper import (
    _is_low_quality_transcript,
    _looks_like_arabic_script,
    _resolve_whisper_language,
)


@pytest.mark.parametrize(
    "text,expected",
    [
        ("یہ میرے علاقے میں پانی کی کمی ہے", True),
        ("हमारे इलाके में पानी की समस्या है", False),
        ("Water supply issue", False),
    ],
)
def test_arabic_script_detection(text, expected):
    assert _looks_like_arabic_script(text) is expected


@override_settings(
    SUPPORTED_LANGUAGES={"hi": "Hindi", "en": "English", "ur": "Urdu"},
    WHISPER_AUTO_LANGUAGE=False,
)
def test_resolve_whisper_language_honours_user_hindi():
    lang, kw, respect = _resolve_whisper_language("hi", __import__("django.conf", fromlist=["settings"]).settings)
    assert lang == "hi"
    assert respect is True
    assert kw.get("temperature") == 0


@override_settings(
    SUPPORTED_LANGUAGES={"hi": "Hindi", "en": "English"},
    WHISPER_AUTO_LANGUAGE=True,
)
def test_resolve_whisper_language_auto_when_empty():
    lang, kw, respect = _resolve_whisper_language(None, __import__("django.conf", fromlist=["settings"]).settings)
    assert lang is None
    assert respect is False


def test_low_quality_hindi_garbage():
    bad = "शिबार वहमन shwah拿au"
    assert _is_low_quality_transcript(bad, "hi", None) is True


def test_realistic_hindi_not_rejected():
    ok = "हमारे गाँव में पानी नहीं आ रहा है कृपया देखें"
    assert _is_low_quality_transcript(ok, "hi", None) is False


def test_good_hindi_transcript():
    good = "हमारे इलाके में पानी की आपूर्ति दो दिन से बंद है"
    assert _is_low_quality_transcript(good, "hi", None) is False
