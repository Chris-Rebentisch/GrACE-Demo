"""Tests for ``src.shared.embeddings`` (D265 Strangler Fig).

CP1 (additive): import-resolution tests verify the new module re-exports
the embedding helpers and that ``entity_resolver`` resolves through it.

CP2 (cutover): functional tests for ``cosine_similarity`` edge cases and
``embed_texts`` against a mocked httpx client. After the cutover the
function bodies live in ``src.shared.embeddings``; ``semantic_strategy``
re-exports them via a one-line shim.
"""

from __future__ import annotations

import importlib

import numpy as np
import pytest


def test_embed_texts_importable_from_shared() -> None:
    """``embed_texts`` is importable from ``src.shared.embeddings``."""
    from src.shared.embeddings import embed_texts  # noqa: F401

    assert callable(embed_texts)


def test_cosine_similarity_importable_from_shared() -> None:
    """``cosine_similarity`` is importable from ``src.shared.embeddings``."""
    from src.shared.embeddings import cosine_similarity  # noqa: F401

    assert callable(cosine_similarity)


def test_entity_resolver_import_chain_resolves() -> None:
    """``src.extraction.entity_resolver`` imports embeddings via the new path."""
    module = importlib.import_module("src.extraction.entity_resolver")
    # Only `embed_texts` is actually used by entity_resolver at runtime;
    # the original assertion for `cosine_similarity` was over-specified
    # (entity_resolver never called it) and a stale top-of-file comment
    # incorrectly implied the dependency. Keep the migration-path check
    # narrow to what the source genuinely re-exports.
    assert hasattr(module, "embed_texts")


def test_semantic_strategy_reexport_shim_resolves() -> None:
    """``src.retrieval.semantic_strategy`` still exposes the helpers (via shim)."""
    module = importlib.import_module("src.retrieval.semantic_strategy")
    assert hasattr(module, "embed_texts")
    assert hasattr(module, "cosine_similarity")


# --- CP2 functional tests -------------------------------------------------


def test_cosine_similarity_zero_query_vector_returns_zeros() -> None:
    """Zero-norm query vector returns a zero vector (no division by zero)."""
    from src.shared.embeddings import cosine_similarity

    matrix = np.array([[1.0, 0.0], [0.0, 1.0], [1.0, 1.0]], dtype=np.float32)
    query = np.array([0.0, 0.0], dtype=np.float32)
    result = cosine_similarity(query, matrix)
    assert result.shape == (3,)
    assert np.allclose(result, 0.0)


def test_cosine_similarity_orthogonal_vectors_return_zero() -> None:
    """Orthogonal vectors yield ~0 cosine similarity."""
    from src.shared.embeddings import cosine_similarity

    matrix = np.array([[0.0, 1.0]], dtype=np.float32)
    query = np.array([1.0, 0.0], dtype=np.float32)
    result = cosine_similarity(query, matrix)
    assert result.shape == (1,)
    assert abs(float(result[0])) < 1e-6


def test_cosine_similarity_identical_vectors_return_one() -> None:
    """Identical (normalized) vectors yield cosine similarity == 1."""
    from src.shared.embeddings import cosine_similarity

    matrix = np.array([[3.0, 4.0]], dtype=np.float32)
    query = np.array([3.0, 4.0], dtype=np.float32)
    result = cosine_similarity(query, matrix)
    assert abs(float(result[0]) - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_embed_texts_calls_ollama_endpoint(monkeypatch) -> None:
    """``embed_texts`` POSTs to ``{base_url}/api/embed`` and returns the
    ``embeddings`` field of the JSON response. Patches ``httpx.AsyncClient``
    at the module ``embed_texts`` actually imports it from (CP1: still
    ``src.retrieval.semantic_strategy``; CP2: ``src.shared.embeddings``).
    Patching ``httpx`` itself works through both states.
    """
    import httpx

    from src.shared.embeddings import embed_texts

    captured: dict[str, object] = {}

    class _DummyResponse:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return self._payload

    class _DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, json):
            captured["url"] = url
            captured["json"] = json
            return _DummyResponse(
                {"embeddings": [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]}
            )

    monkeypatch.setattr(httpx, "AsyncClient", _DummyClient)
    # Legacy inference path: no explicit provider → an :11434 URL means Ollama.
    # (Some pytest plugins export the repo .env into os.environ, so be explicit.)
    monkeypatch.delenv("GRACE_EMBED_PROVIDER", raising=False)

    result = await embed_texts(
        ["alpha", "beta"],
        base_url="http://127.0.0.1:11434",
        model="nomic-embed-text",
    )

    assert result == [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    assert captured["url"] == "http://127.0.0.1:11434/api/embed"
    assert captured["json"] == {
        "model": "nomic-embed-text",
        "input": ["alpha", "beta"],
    }


@pytest.mark.asyncio
async def test_embed_texts_openai_compatible_when_provider_set(monkeypatch) -> None:
    """Cloud embeddings use ``/v1/embeddings`` and keep 768-dim vectors."""
    import httpx

    from src.shared.embeddings import embed_texts

    monkeypatch.setenv("GRACE_EMBED_PROVIDER", "openai")
    monkeypatch.setenv("GRACE_EMBED_BASE_URL", "https://api.openai.com/v1")
    monkeypatch.setenv("GRACE_EMBED_MODEL", "text-embedding-3-small")
    monkeypatch.setenv("GRACE_EMBED_DIMENSIONS", "768")
    monkeypatch.setenv("LLM_API_KEY", "sk-test")

    captured: dict[str, object] = {}

    class _DummyResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return {
                "data": [
                    {"index": 0, "embedding": [0.1] * 3},
                    {"index": 1, "embedding": [0.2] * 3},
                ]
            }

    class _DummyClient:
        def __init__(self, *args, **kwargs) -> None:
            captured["client_kwargs"] = kwargs

        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

        async def post(self, url, headers=None, json=None):
            captured["url"] = url
            captured["headers"] = headers
            captured["json"] = json
            return _DummyResponse()

    monkeypatch.setattr(httpx, "AsyncClient", _DummyClient)

    result = await embed_texts(
        ["Alpha Corp", "Beta LLC"],
        base_url="http://localhost:11434",
        model="nomic-embed-text",
    )

    assert result == [[0.1] * 3, [0.2] * 3]
    assert captured["url"] == "https://api.openai.com/v1/embeddings"
    assert captured["json"]["model"] == "text-embedding-3-small"
    assert captured["json"]["dimensions"] == 768
    assert captured["headers"]["Authorization"] == "Bearer sk-test"


# --- GrACE-Demo: embeddings are optional (cloud-only students) -----------------


def test_resolve_embed_provider_none_values(monkeypatch) -> None:
    from src.shared.embeddings import embeddings_enabled, resolve_embed_provider

    for value in ("none", "off", "disabled", "NONE"):
        monkeypatch.setenv("GRACE_EMBED_PROVIDER", value)
        assert resolve_embed_provider("http://127.0.0.1:11434") == "none"
        assert embeddings_enabled("http://127.0.0.1:11434") is False


def test_resolve_embed_provider_auto_prefers_dedicated_key(monkeypatch) -> None:
    from src.shared.embeddings import resolve_embed_provider

    monkeypatch.setenv("GRACE_EMBED_PROVIDER", "auto")
    monkeypatch.setenv("GRACE_EMBED_API_KEY", "sk-test-embed")
    assert resolve_embed_provider() == "openai"


def test_resolve_embed_provider_auto_without_any_key_is_none(monkeypatch) -> None:
    from src.shared import embeddings as mod

    monkeypatch.setenv("GRACE_EMBED_PROVIDER", "auto")
    monkeypatch.delenv("GRACE_EMBED_API_KEY", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.setattr(mod, "_chat_vendor_serves_openai_embeddings", lambda: False)
    assert mod.resolve_embed_provider() == "none"


def test_resolve_embed_provider_auto_reuses_openai_chat_key(monkeypatch) -> None:
    from src.shared import embeddings as mod

    monkeypatch.setenv("GRACE_EMBED_PROVIDER", "auto")
    monkeypatch.delenv("GRACE_EMBED_API_KEY", raising=False)
    monkeypatch.setenv("LLM_API_KEY", "sk-test-chat")
    monkeypatch.setattr(mod, "_chat_vendor_serves_openai_embeddings", lambda: True)
    assert mod.resolve_embed_provider() == "openai"
    monkeypatch.setattr(mod, "_chat_vendor_serves_openai_embeddings", lambda: False)
    assert mod.resolve_embed_provider() == "none"


@pytest.mark.asyncio
async def test_embed_texts_raises_typed_error_when_disabled(monkeypatch) -> None:
    from src.shared.embeddings import EmbeddingsDisabled, embed_texts

    monkeypatch.setenv("GRACE_EMBED_PROVIDER", "none")
    with pytest.raises(EmbeddingsDisabled):
        await embed_texts(["alpha"], base_url="http://127.0.0.1:11434")


@pytest.mark.asyncio
async def test_semantic_index_degrades_when_disabled(monkeypatch) -> None:
    """With embeddings off, the semantic strategy is empty instead of crashing
    (BM25 + graph strategies carry /api/retrieval/query)."""
    from src.retrieval.semantic_strategy import SemanticSearchIndex

    monkeypatch.setenv("GRACE_EMBED_PROVIDER", "none")
    idx = SemanticSearchIndex("http://127.0.0.1:11434")
    await idx.build_index([("g1", "Alpha: thing"), ("g2", "Beta: other")])
    assert idx.embeddings is None
    assert await idx.search("alpha") == []
