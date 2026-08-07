"""
Model registry — save and load versioned sklearn classifiers.
Models are persisted as joblib files under BASE_DIR/ml_models/.
"""
import logging
import os
from pathlib import Path
from django.conf import settings

logger = logging.getLogger(__name__)

MODELS_DIR = Path(getattr(settings, "BASE_DIR", ".")) / "ml_models"


def _ensure_dir():
    MODELS_DIR.mkdir(parents=True, exist_ok=True)


def save_model(pipeline, version: str = "latest") -> str:
    """Persist a sklearn pipeline. Returns the saved file path."""
    try:
        import joblib
        _ensure_dir()
        path = str(MODELS_DIR / f"classifier_{version}.joblib")
        joblib.dump(pipeline, path)
        logger.info("Model saved → %s", path)
        return path
    except ImportError:
        logger.warning("joblib not installed; model not saved.")
        return ""


def load_model(version: str = "latest"):
    """Load and return a persisted sklearn pipeline, or None."""
    try:
        import joblib
        path = MODELS_DIR / f"classifier_{version}.joblib"
        if path.exists():
            model = joblib.load(str(path))
            logger.info("Model loaded from %s", path)
            return model
        logger.info("No saved model at %s", path)
    except ImportError:
        logger.warning("joblib not installed; cannot load model.")
    except Exception as exc:
        logger.exception("Failed to load model: %s", exc)
    return None


def list_versions() -> list[str]:
    """Return available model version names."""
    _ensure_dir()
    return [
        p.stem.replace("classifier_", "")
        for p in MODELS_DIR.glob("classifier_*.joblib")
    ]
