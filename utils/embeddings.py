import hashlib
import os
import sqlite3
from typing import Any, Dict, List, Optional

import numpy as np
import ollama
from sklearn.metrics.pairwise import cosine_similarity


class EmbeddingError(RuntimeError):
    """Raised when an embedding cannot be produced (Ollama down, model missing, bad response)."""


class EmbeddingUtil:
    """Utility for creating embeddings using Ollama.

    Embeddings are cached (in memory, and on disk in a small SQLite file) so each
    unique text is embedded once, not once per JD/CV pair. Failures raise
    ``EmbeddingError`` instead of returning a fake vector, so a run can never
    silently produce scores from missing data.
    """

    def __init__(self, model: Optional[str] = None, cache_path: Optional[str] = None):
        """Initialize embedding utility

        Args:
            model: Ollama embedding model (default: $OLLAMA_EMBED_MODEL or nomic-embed-text)
            cache_path: SQLite file for the on-disk cache (default: $EMBEDDING_CACHE or
                embedding_cache.db). Pass "" to disable the disk cache.
        """
        self.model = model or os.environ.get("OLLAMA_EMBED_MODEL", "nomic-embed-text")
        if cache_path is None:
            cache_path = os.environ.get("EMBEDDING_CACHE", "embedding_cache.db")
        self.cache_path = cache_path
        self._memory_cache: Dict[str, List[float]] = {}
        if self.cache_path:
            self._init_disk_cache()

    # ------------------------------------------------------------------ cache
    def _key(self, text: str) -> str:
        return hashlib.sha256(f"{self.model}\x00{text}".encode("utf-8")).hexdigest()

    def _init_disk_cache(self) -> None:
        try:
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute(
                    "CREATE TABLE IF NOT EXISTS embeddings (key TEXT PRIMARY KEY, vector BLOB)"
                )
        except sqlite3.Error:
            self.cache_path = ""  # cache is an optimisation; never fail because of it

    def _disk_get(self, key: str) -> Optional[List[float]]:
        if not self.cache_path:
            return None
        try:
            with sqlite3.connect(self.cache_path) as conn:
                row = conn.execute("SELECT vector FROM embeddings WHERE key = ?", (key,)).fetchone()
            if row:
                return np.frombuffer(row[0], dtype=np.float32).astype(float).tolist()
        except sqlite3.Error:
            pass
        return None

    def _disk_put(self, key: str, vector: List[float]) -> None:
        if not self.cache_path:
            return
        try:
            blob = np.asarray(vector, dtype=np.float32).tobytes()
            with sqlite3.connect(self.cache_path) as conn:
                conn.execute(
                    "INSERT OR REPLACE INTO embeddings (key, vector) VALUES (?, ?)", (key, blob)
                )
        except sqlite3.Error:
            pass

    # ----------------------------------------------------------------- ollama
    def _embed_remote(self, text: str) -> List[float]:
        try:
            response = ollama.embeddings(model=self.model, prompt=text)
        except Exception as e:  # connection refused, model not found, timeout...
            raise EmbeddingError(
                f"Could not get an embedding from Ollama ({e}). "
                f"Is Ollama running, and have you run `ollama pull {self.model}`?"
            ) from e

        embedding = None
        if response is not None:
            try:
                embedding = response["embedding"]
            except (KeyError, TypeError):
                embedding = getattr(response, "embedding", None)
        if not embedding:
            raise EmbeddingError(f"Ollama returned no embedding for model '{self.model}'.")
        return list(embedding)

    def check_available(self) -> None:
        """Fail fast with a helpful message if embeddings cannot be produced."""
        self._embed_remote("ping")

    def get_embedding(self, text: str) -> List[float]:
        """Get embedding for text (cached). Raises EmbeddingError on failure."""
        key = self._key(text)
        if key in self._memory_cache:
            return self._memory_cache[key]
        cached = self._disk_get(key)
        if cached is not None:
            self._memory_cache[key] = cached
            return cached
        vector = self._embed_remote(text)
        self._memory_cache[key] = vector
        self._disk_put(key, vector)
        return vector

    # ------------------------------------------------------------ formatting
    def _format_jd_text(self, jd_data: Dict[str, Any]) -> str:
        """Format JD data as text for embedding"""
        title = jd_data.get('title', '')
        skills = jd_data.get('summary', {}).get('required_skills', [])
        if isinstance(skills, list):
            skills_text = ", ".join(skills)
        else:
            skills_text = skills

        education = jd_data.get('summary', {}).get('education', '')
        experience = jd_data.get('summary', {}).get('years_of_experience', '')
        certifications = jd_data.get('summary', {}).get('certifications', [])
        if isinstance(certifications, list):
            certifications_text = ", ".join(certifications)
        else:
            certifications_text = certifications

        responsibilities = jd_data.get('summary', {}).get('responsibilities', [])
        if isinstance(responsibilities, list):
            responsibilities_text = ". ".join(responsibilities)
        else:
            responsibilities_text = responsibilities

        text = f"""
        Job Title: {title}
        Required Skills: {skills_text}
        Education: {education}
        Experience: {experience}
        Certifications: {certifications_text}
        Responsibilities: {responsibilities_text}
        """
        return text.strip()

    def _format_cv_text(self, cv_data: Dict[str, Any]) -> str:
        """Format CV data as text for embedding"""
        name = cv_data.get('name', '')
        education = cv_data.get('education', '')
        experience = cv_data.get('work_experience', '')
        skills = cv_data.get('skills', '')
        certifications = cv_data.get('certifications', '')
        tech_stack = cv_data.get('tech_stack', '')

        text = f"""
        Name: {name}
        Education: {education}
        Experience: {experience}
        Skills: {skills}
        Certifications: {certifications}
        Technologies: {tech_stack}
        """
        return text.strip()

    def get_jd_embedding(self, jd_data: Dict[str, Any]) -> List[float]:
        """Get embedding for job description data"""
        return self.get_embedding(self._format_jd_text(jd_data))

    def get_cv_embedding(self, cv_data: Dict[str, Any]) -> List[float]:
        """Get embedding for CV data"""
        return self.get_embedding(self._format_cv_text(cv_data))

    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Cosine similarity between two embeddings, as a percentage (0-100)"""
        emb1 = np.array(embedding1, dtype=float).reshape(1, -1)
        emb2 = np.array(embedding2, dtype=float).reshape(1, -1)
        if not np.linalg.norm(emb1) or not np.linalg.norm(emb2):
            return 0.0
        return float(cosine_similarity(emb1, emb2)[0][0] * 100)
