"""Strategy 2: Semantic search via Ollama nomic-embed-text embeddings."""

from __future__ import annotations

import numpy as np
import structlog

from src.retrieval.retrieval_models import RetrievalCandidate

# D265 Strangler Fig: bodies moved to src/shared/embeddings.py (Chunk 35a).
# Re-export for backward compatibility with retrieval-internal callers.
from src.shared.embeddings import (  # noqa: F401
    EmbeddingsDisabled,
    cosine_similarity,
    embed_texts,
    embeddings_enabled,
)

logger = structlog.get_logger()


class SemanticSearchIndex:
    """In-memory semantic search over entity text representations.

    Uses Ollama nomic-embed-text for embeddings and numpy cosine similarity.
    No external vector DB — embeddings stored in memory as numpy arrays.
    """

    def __init__(self, ollama_base_url: str, model: str = "nomic-embed-text"):
        self.ollama_base_url = ollama_base_url
        self.model = model
        self.grace_ids: list[str] = []
        self.texts: list[str] = []
        self.embeddings: np.ndarray | None = None

    async def build_index(self, entities: list[tuple[str, str]]) -> None:
        """Embed all (grace_id, text) pairs and store as numpy matrix."""
        if not entities:
            self.grace_ids = []
            self.texts = []
            self.embeddings = None
            return

        # GrACE-Demo: embeddings are optional (cloud-only students may have no
        # embeddings vendor). Without vectors the semantic strategy is simply
        # empty and BM25 + graph strategies carry retrieval.
        if not embeddings_enabled(self.ollama_base_url):
            logger.info("semantic_index.skipped_embeddings_disabled", entity_count=len(entities))
            self.grace_ids = []
            self.texts = []
            self.embeddings = None
            return

        self.grace_ids = [gid for gid, _ in entities]
        self.texts = [text for _, text in entities]

        # Batch embed all texts. A backend failure must not take the whole
        # index build (and every /api/retrieval/query) down with it.
        try:
            vectors = await embed_texts(self.texts, self.ollama_base_url, self.model)
        except Exception as exc:  # noqa: BLE001 — degrade to keyword/graph retrieval
            logger.warning(
                "semantic_index.build_failed_degrading",
                error=str(exc),
                error_type=type(exc).__name__,
                advice="Semantic strategy disabled for this index; BM25 + graph still serve queries.",
            )
            self.grace_ids = []
            self.texts = []
            self.embeddings = None
            return
        self.embeddings = np.array(vectors, dtype=np.float32)
        logger.info(
            "semantic_index.built",
            entity_count=len(self.grace_ids),
            dim=self.embeddings.shape[1] if self.embeddings.ndim == 2 else 0,
        )

    async def search(
        self, query_text: str, top_k: int = 50
    ) -> list[RetrievalCandidate]:
        """Embed query, compute cosine similarity, return top-K."""
        if self.embeddings is None or len(self.grace_ids) == 0:
            return []

        try:
            query_vectors = await embed_texts(
                [query_text], self.ollama_base_url, self.model
            )
        except Exception as exc:  # noqa: BLE001 — degrade, never fail the query
            logger.warning("semantic_search.embed_failed_degrading", error=str(exc))
            return []
        query_vec = np.array(query_vectors[0], dtype=np.float32)

        similarities = cosine_similarity(query_vec, self.embeddings)
        top_indices = np.argsort(similarities)[::-1][:top_k]

        candidates: list[RetrievalCandidate] = []
        for rank, idx in enumerate(top_indices):
            score = float(similarities[idx])
            if score <= 0:
                continue
            candidates.append(
                RetrievalCandidate(
                    grace_id=self.grace_ids[idx],
                    entity_type="Entity",  # Type not stored in index
                    name=self.texts[idx].split(":")[0] if ":" in self.texts[idx] else "",
                    score=score,
                    strategy="semantic",
                    rank=rank + 1,
                )
            )

        return candidates
