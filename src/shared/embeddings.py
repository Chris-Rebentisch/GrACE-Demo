"""Canonical home for embedding helpers (D265 Strangler Fig).

Chunk 35a CP2 (cutover): the function bodies live here after migration
from ``src/retrieval/semantic_strategy.py:14-41``. ``semantic_strategy``
retains a thin re-export shim for backward compatibility with retrieval-
internal callers.

Direction of imports is one-way: ``semantic_strategy`` imports from
``src.shared.embeddings``, never the reverse. This avoids circular
imports.

The CF3 retrieval lock (``scripts/check-retrieval-unchanged.sh``) gains
a scoped allowlist for the ``semantic_strategy.py`` shim only.
"""

from __future__ import annotations

import os

import httpx
import numpy as np

__all__ = [
    "EmbeddingsDisabled",
    "cosine_similarity",
    "embed_texts",
    "embeddings_enabled",
    "resolve_embed_provider",
]


class EmbeddingsDisabled(RuntimeError):
    """Raised by :func:`embed_texts` when embeddings are switched off.

    GrACE-Demo runs on whatever cloud LLM the student already has. Most chat
    vendors (Anthropic, DeepSeek, Groq, ...) do not serve an embeddings
    endpoint, so vectors are optional: callers that can degrade (semantic
    retrieval, ANN entity resolution, coverage mapping) check
    :func:`embeddings_enabled` first and fall back to keyword / exact-match
    behaviour. Anything that reaches ``embed_texts`` anyway gets this typed
    error instead of a connection failure to a non-existent Ollama.
    """


_DISABLED_VALUES = {"none", "off", "disabled", "false", "0"}
_OPENAI_VALUES = {"openai", "openai_compatible", "cloud"}
_OLLAMA_VALUES = {"ollama", "local"}
_AUTO_VALUES = {"", "auto"}

# Default HTTP timeout for the Ollama /api/embed call. Overridable per call
# via the `timeout` parameter, or globally via GRACE_EMBED_TIMEOUT_SECONDS.
_DEFAULT_EMBED_TIMEOUT_SECONDS = 120.0


def _default_embed_timeout() -> float:
    """Resolve the default embed timeout (env override, else 120s)."""
    raw = os.environ.get("GRACE_EMBED_TIMEOUT_SECONDS")
    if raw:
        try:
            return float(raw)
        except ValueError:
            pass
    return _DEFAULT_EMBED_TIMEOUT_SECONDS


# Phase-5 fix: nomic-embed-text returns HTTP 400 "input length exceeds the
# context length" on items above its 8K-token window. Defensively truncate
# per-item at the call site so every caller (corpus builder, query embedder,
# entity-resolver) is robust to upstream text bloat. 6000 chars leaves
# headroom even for token-dense inputs.
_EMBED_MAX_CHARS_PER_ITEM = 6000


def _chat_vendor_serves_openai_embeddings() -> bool:
    """True when the configured *chat* vendor is real OpenAI (same key works
    for ``/v1/embeddings``). DeepSeek / Groq / Together etc. also use
    ``provider: openai`` but do not serve embeddings, so match on the host.
    Best-effort — never raises (used from the ``auto`` resolver)."""
    try:
        from src.shared.llm_provider import read_llm_config_from_yaml  # lazy: avoid cycles

        cfg = read_llm_config_from_yaml()
    except Exception:  # noqa: BLE001 — config unreadable → assume no
        return False
    if (cfg.get("provider") or "").lower() != "openai":
        return False
    base_url = (cfg.get("base_url") or "").strip().lower()
    # Empty base_url means the provider's own default, which is api.openai.com.
    return (not base_url) or ("api.openai.com" in base_url)


def resolve_embed_provider(base_url: str = "") -> str:
    """Resolve the embeddings backend: ``"openai"`` | ``"ollama"`` | ``"none"``.

    ``GRACE_EMBED_PROVIDER`` (``.env``):

    * ``none`` / ``off`` / ``disabled`` — vectors off (see :class:`EmbeddingsDisabled`).
    * ``openai`` / ``cloud`` — OpenAI-compatible ``/v1/embeddings``
      (``GRACE_EMBED_BASE_URL`` / ``GRACE_EMBED_MODEL`` / ``GRACE_EMBED_API_KEY``).
    * ``ollama`` / ``local`` — local Ollama ``/api/embed``.
    * ``auto`` (**GrACE-Demo default**) — use OpenAI-compatible embeddings when a
      dedicated ``GRACE_EMBED_API_KEY`` is set, or when the chat vendor in
      ``config/discovery.yaml`` is real OpenAI (its ``LLM_API_KEY`` is reused);
      otherwise **none**. A student with only an Anthropic / DeepSeek / Groq
      key therefore gets keyword + graph retrieval instead of a 401.
    * unset — legacy behaviour: infer from ``base_url`` (``:11434`` → Ollama,
      ``/v1`` → OpenAI-compatible) so pre-Demo installs and unit tests keep working.

    ArcadeDB vector indexes stay 768-dim (``GRACE_EMBED_DIMENSIONS``).
    """
    explicit = (os.environ.get("GRACE_EMBED_PROVIDER") or "").strip().lower()
    if explicit in _DISABLED_VALUES:
        return "none"
    if explicit in _OPENAI_VALUES:
        return "openai"
    if explicit in _OLLAMA_VALUES:
        return "ollama"
    if explicit == "auto":
        if (os.environ.get("GRACE_EMBED_API_KEY") or "").strip():
            return "openai"
        if (os.environ.get("LLM_API_KEY") or "").strip() and _chat_vendor_serves_openai_embeddings():
            return "openai"
        return "none"
    if explicit not in _AUTO_VALUES:
        # Unknown value: fail closed rather than silently calling a local Ollama.
        return "none"
    lowered = (base_url or "").lower()
    if "11434" in lowered or lowered.rstrip("/").endswith("/api"):
        return "ollama"
    if "/v1" in lowered or "openai" in lowered or "deepseek" in lowered:
        return "openai"
    return "ollama"


def embeddings_enabled(base_url: str = "") -> bool:
    """False when no embeddings backend is available (see :func:`resolve_embed_provider`).

    Callers use this to skip vector work up-front (semantic retrieval, ANN
    entity resolution, coverage mapping) instead of catching a failed HTTP call.
    """
    return resolve_embed_provider(base_url) != "none"


# Backwards-compatible private alias (older callers / tests).
_embed_provider = resolve_embed_provider


async def embed_texts(
    texts: list[str],
    base_url: str,
    model: str = "nomic-embed-text",
    timeout: float | None = None,
) -> list[list[float]]:
    """Embed texts via Ollama ``/api/embed`` or OpenAI-compatible ``/v1/embeddings``.

    ``timeout`` is the HTTP timeout in seconds; defaults to 120 (or the
    GRACE_EMBED_TIMEOUT_SECONDS env var when set).
    """
    if timeout is None:
        timeout = _default_embed_timeout()
    provider = resolve_embed_provider(base_url)
    if provider == "none":
        raise EmbeddingsDisabled(
            "Embeddings are disabled (GRACE_EMBED_PROVIDER resolved to 'none': no "
            "OpenAI-compatible embeddings key is configured). Retrieval degrades to "
            "keyword + graph search; entity resolution to exact/alias matching. Set "
            "GRACE_EMBED_API_KEY (OpenAI-compatible) or GRACE_EMBED_PROVIDER=ollama "
            "to enable vectors."
        )
    truncated = [
        (t[:_EMBED_MAX_CHARS_PER_ITEM] if isinstance(t, str) else "")
        for t in texts
    ]
    if provider == "ollama":
        # F-006: Ollama nomic-embed-text can collapse proper names unless
        # lowercased. Cloud embedding APIs do not need this.
        truncated = [t.lower() for t in truncated]
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url.rstrip('/')}/api/embed",
                json={"model": model, "input": truncated},
            )
            resp.raise_for_status()
            return resp.json()["embeddings"]

    embed_base = (
        os.environ.get("GRACE_EMBED_BASE_URL")
        or "https://api.openai.com/v1"
    ).rstrip("/")
    embed_model = os.environ.get("GRACE_EMBED_MODEL") or "text-embedding-3-small"
    dimensions = int(os.environ.get("GRACE_EMBED_DIMENSIONS") or "768")
    api_key = (
        os.environ.get("GRACE_EMBED_API_KEY")
        or os.environ.get("LLM_API_KEY")
        or ""
    )
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    payload: dict = {"model": embed_model, "input": truncated}
    if dimensions > 0:
        payload["dimensions"] = dimensions
    async with httpx.AsyncClient(timeout=timeout) as client:
        resp = await client.post(
            f"{embed_base}/embeddings",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        body = resp.json()
        rows = sorted(body.get("data") or [], key=lambda row: row.get("index", 0))
        return [row["embedding"] for row in rows]


def cosine_similarity(query_vec: np.ndarray, matrix: np.ndarray) -> np.ndarray:
    """Compute cosine similarity between query vector and all rows in matrix."""
    query_norm = np.linalg.norm(query_vec)
    if query_norm == 0:
        return np.zeros(matrix.shape[0])
    normed_query = query_vec / query_norm

    row_norms = np.linalg.norm(matrix, axis=1, keepdims=True)
    # Avoid division by zero
    row_norms = np.where(row_norms == 0, 1, row_norms)
    normed_matrix = matrix / row_norms

    return normed_matrix @ normed_query
