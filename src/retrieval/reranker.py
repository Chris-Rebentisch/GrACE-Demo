"""Cross-encoder reranking wrapper using sentence-transformers."""

from __future__ import annotations

import structlog

from src.retrieval.retrieval_models import FusedCandidate, RankedResult
from src.retrieval.text_representation import entity_to_text

try:  # heavy import; keep the module importable even if the dependency is absent
    from sentence_transformers import CrossEncoder
except Exception:  # noqa: BLE001 — pragma: no cover
    CrossEncoder = None  # type: ignore[assignment]

logger = structlog.get_logger()


class CrossEncoderReranker:
    """Wrapper around sentence-transformers CrossEncoder.

    Loads ms-marco-MiniLM-L-6-v2 on CPU. Reranks top-N RRF candidates.

    GrACE-Demo resilience: the model is loaded lazily on first use. If it
    cannot be loaded (fresh machine with ``HF_HUB_OFFLINE=1`` and no cached
    model, or sentence-transformers unavailable) the reranker degrades to
    RRF order instead of failing every ``/api/retrieval/query`` with a 500.
    Prefetch once with ``bash scripts/prefetch-models.sh`` to enable it.
    """

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        self.model_name = model_name
        self.model = None
        self._load_attempted = False
        self._load_error: str | None = None

    def _ensure_model(self) -> None:
        if self._load_attempted:
            return
        self._load_attempted = True
        try:
            if CrossEncoder is None:
                raise RuntimeError("sentence_transformers is not installed")
            self.model = CrossEncoder(self.model_name)
        except Exception as exc:  # noqa: BLE001 — degrade to RRF order
            self._load_error = f"{type(exc).__name__}: {exc}"
            self.model = None
            logger.warning(
                "reranker.model_unavailable_degrading_to_rrf",
                model=self.model_name,
                error=self._load_error[:300],
                advice=(
                    "Cross-encoder reranker could not be loaded; results keep RRF "
                    "fusion order. Run `bash scripts/prefetch-models.sh` (network "
                    "required once) to enable reranking."
                ),
            )

    @property
    def available(self) -> bool:
        self._ensure_model()
        return self.model is not None

    def rerank(
        self,
        query: str,
        candidates: list[FusedCandidate],
        top_k: int = 10,
    ) -> list[RankedResult]:
        """Score each candidate against the query, return top-K by rerank score.

        Pairs: [(query, candidate_text), ...] for each candidate.
        candidate_text = entity_to_text(candidate.entity_type, candidate.properties)
        """
        if not candidates:
            return []

        self._ensure_model()
        if self.model is None:
            # Degraded mode: keep fusion order, expose the RRF score as the
            # rerank score so downstream banding still has a monotone signal.
            return [
                RankedResult(
                    grace_id=c.grace_id,
                    entity_type=c.entity_type,
                    name=c.name,
                    properties=c.properties,
                    rerank_score=float(c.rrf_score),
                    rrf_score=c.rrf_score,
                    contributing_strategies=c.contributing_strategies,
                )
                for c in candidates[:top_k]
            ]

        pairs = [
            [query, entity_to_text(c.entity_type, c.properties)]
            for c in candidates
        ]
        scores = self.model.predict(pairs)

        # Pair scores with candidates
        scored = list(zip(scores, candidates))
        scored.sort(key=lambda x: float(x[0]), reverse=True)

        results: list[RankedResult] = []
        for score, candidate in scored[:top_k]:
            results.append(
                RankedResult(
                    grace_id=candidate.grace_id,
                    entity_type=candidate.entity_type,
                    name=candidate.name,
                    properties=candidate.properties,
                    rerank_score=float(score),
                    rrf_score=candidate.rrf_score,
                    contributing_strategies=candidate.contributing_strategies,
                )
            )

        return results
