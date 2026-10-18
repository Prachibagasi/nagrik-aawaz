import pytest

from utils.embeddings import EmbeddingError, EmbeddingUtil


def test_same_text_is_embedded_once(fake_ollama):
    e = EmbeddingUtil(cache_path="")
    e.get_embedding("hello world")
    e.get_embedding("hello world")
    assert fake_ollama == ["hello world"]


def test_disk_cache_survives_a_new_instance(fake_ollama, tmp_path):
    path = str(tmp_path / "cache.db")
    EmbeddingUtil(cache_path=path).get_embedding("persist me")
    second = EmbeddingUtil(cache_path=path)
    vector = second.get_embedding("persist me")
    assert len(fake_ollama) == 1          # second instance never called Ollama
    assert len(vector) == 64


def test_failure_raises_instead_of_returning_zero_vector(monkeypatch):
    def boom(model, prompt):
        raise ConnectionError("connection refused")
    monkeypatch.setattr("utils.embeddings.ollama.embeddings", boom)
    with pytest.raises(EmbeddingError, match="ollama pull"):
        EmbeddingUtil(cache_path="").get_embedding("anything")


def test_empty_response_raises(monkeypatch):
    monkeypatch.setattr("utils.embeddings.ollama.embeddings", lambda model, prompt: {})
    with pytest.raises(EmbeddingError):
        EmbeddingUtil(cache_path="").get_embedding("anything")


def test_check_available_ok_and_failing(fake_ollama, monkeypatch):
    EmbeddingUtil(cache_path="").check_available()
    monkeypatch.setattr("utils.embeddings.ollama.embeddings",
                        lambda model, prompt: (_ for _ in ()).throw(ConnectionError("down")))
    with pytest.raises(EmbeddingError):
        EmbeddingUtil(cache_path="").check_available()


def test_identical_vectors_score_100_and_zero_vector_scores_0():
    e = EmbeddingUtil(cache_path="")
    assert e.calculate_similarity([1, 2, 3], [1, 2, 3]) == pytest.approx(100.0)
    assert e.calculate_similarity([0, 0, 0], [1, 2, 3]) == 0.0


def test_model_is_configurable_via_env(monkeypatch):
    monkeypatch.setenv("OLLAMA_EMBED_MODEL", "mxbai-embed-large")
    assert EmbeddingUtil(cache_path="").model == "mxbai-embed-large"
