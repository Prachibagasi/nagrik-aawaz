import hashlib
import os
import sys
from pathlib import Path

import numpy as np
import pytest
from rest_framework_simplejwt.tokens import RefreshToken

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from utils.embeddings import EmbeddingUtil  # noqa: E402


def bearer(user):
    """Build an authenticated request header for civic API tests."""
    token = RefreshToken.for_user(user)
    return {"HTTP_AUTHORIZATION": f"Bearer {token.access_token}"}


@pytest.fixture(autouse=True)
def _no_disk_cache(monkeypatch):
    """Tests must never create embedding_cache.db in the project folder."""
    monkeypatch.setenv("EMBEDDING_CACHE", "")


def fake_vector(text: str, dims: int = 64) -> list:
    """Deterministic bag-of-words embedding: texts sharing words score higher."""
    vec = np.zeros(dims)
    for token in text.lower().split():
        h = int(hashlib.md5(token.encode()).hexdigest(), 16)
        vec[h % dims] += 1.0
    return vec.tolist()


@pytest.fixture
def fake_ollama(monkeypatch):
    """Replace ollama.embeddings with the fake above; records every call."""
    calls = []

    def _embeddings(model, prompt):
        calls.append(prompt)
        return {"embedding": fake_vector(prompt)}

    monkeypatch.setattr("utils.embeddings.ollama.embeddings", _embeddings)
    return calls


@pytest.fixture
def embedder(fake_ollama):
    return EmbeddingUtil(cache_path="")


@pytest.fixture
def resumes_dir():
    return ROOT / "resumes"


@pytest.fixture
def jd_csv():
    return ROOT / "job_description.csv"
