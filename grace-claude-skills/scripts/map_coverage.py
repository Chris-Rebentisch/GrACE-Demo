#!/usr/bin/env python3
"""STEP 3 (propose-time, no chat LLM) — Map CQ coverage onto an LLM-authored proposal.

Assigns each competency question to the entity types / relationships that answer
it and writes the result back into the SeedSchema:

Two modes, chosen automatically:
  * embeddings available (GRACE_EMBED_PROVIDER resolves to a vendor): cosine
    similarity between CQ text and type/relationship descriptions.
  * embeddings disabled (GrACE-Demo cloud-only default with an Anthropic /
    DeepSeek / Groq key): keep any `answerable_cqs` the authoring LLM already
    filled in, top up with lexical (token-overlap) matching, and report that in
    the output. Good enough for a classroom corpus; the authoring LLM remains
    the primary source of coverage — see grace-ontology-proposal/SKILL.md.

Fields written:

  * entity_types[].answerable_cqs   <- CQs each type answers
  * relationships[].answerable_cqs  <- CQs each relationship answers
  * coverage_matrix[]               <- per-CQ {cq_id, cq_text, covered_by_types,
                                       covered_by_relationships, coverage_status}
  * quality_metrics.cq_coverage_rate

So the ratified version records which CQ every type/relationship answers, and
which CQs are still uncovered.

Usage:
  python3 map_coverage.py --in ./workspace/seed_schema.json --domain legal
  python3 map_coverage.py --in ./workspace/seed_schema.json --cqs ./workspace/cqs.json
  python3 map_coverage.py --in ./workspace/seed_schema.json --domain legal --threshold 0.5
"""
from __future__ import annotations

import argparse
import asyncio
import json
from pathlib import Path

import numpy as np

from _common import add_grace_to_path, route_logs_to_stderr, get_session


def _load_cqs_from_db(grace_root: str | None, domain: str) -> list[dict]:
    db = get_session(grace_root)
    from src.discovery.cq_database import CompetencyQuestionRow  # noqa: E402

    rows = (
        db.query(CompetencyQuestionRow)
        .filter(CompetencyQuestionRow.domain == domain,
                CompetencyQuestionRow.status != "REJECTED")
        .all()
    )
    return [{"id": str(r.id), "text": r.canonical_text} for r in rows]


def _load_cqs_from_file(path: str) -> list[dict]:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    out = []
    for i, c in enumerate(raw):
        t = (c.get("canonical_text") or c.get("question") or "").strip()
        if t:
            out.append({"id": c.get("id", f"cq{i:03d}"), "text": t})
    return out


_STOP = {"a", "an", "the", "of", "in", "on", "for", "to", "and", "or", "is", "are", "was",
         "were", "be", "by", "with", "which", "what", "who", "whom", "whose", "when", "where",
         "how", "does", "do", "did", "that", "this", "these", "those", "it", "its", "as", "at",
         "from", "has", "have", "had", "can", "may", "any", "all", "each", "per", "under"}


def _norm(text: str) -> str:
    return " ".join((text or "").lower().split())


def _tokens(text: str) -> set[str]:
    out = set()
    for raw in (text or "").lower().replace("_", " ").split():
        tok = "".join(ch for ch in raw if ch.isalnum())
        if len(tok) > 2 and tok not in _STOP:
            out.add(tok)
            if tok.endswith("s"):  # crude plural fold: claims ~ claim
                out.add(tok[:-1])
    return out


def _lexical_sims(query: str, docs: list[str]) -> np.ndarray:
    """Token-overlap similarity (|Q∩D| / |Q|) — a vectors-free stand-in for cosine."""
    q = _tokens(query)
    if not q or not docs:
        return np.zeros(len(docs))
    return np.array([len(q & _tokens(d)) / len(q) for d in docs], dtype=float)


def _type_text(t: dict) -> str:
    return f"{t.get('name','')}: {t.get('description','')} {t.get('plain_description','')}".strip()


def _rel_text(r: dict) -> str:
    return (f"{r.get('name','')} ({r.get('source_type','')} -> {r.get('target_type','')}): "
            f"{r.get('description','')} {r.get('plain_description','')}").strip()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--grace-root", default=None)
    ap.add_argument("--in", dest="infile", required=True, help="LLM-authored seed_schema.json")
    ap.add_argument("--out", default=None, help="Output path (default: overwrite --in)")
    ap.add_argument("--domain", default=None, help="Pull CQs from DB for this domain")
    ap.add_argument("--cqs", default=None, help="OR read CQs from this cqs.json")
    ap.add_argument("--threshold", type=float, default=0.5, help="Cosine threshold for a match")
    ap.add_argument("--top-k", type=int, default=3, help="Max types/rels assigned per CQ")
    ap.add_argument("--base-url", default="http://localhost:11434",
                    help="Embedding base URL when GRACE_EMBED_PROVIDER=ollama (ignored for cloud/none)")
    ap.add_argument("--lexical", action="store_true",
                    help="Force lexical (token-overlap) mode even if embeddings are available")
    args = ap.parse_args()

    add_grace_to_path(args.grace_root)
    route_logs_to_stderr(quiet=True)
    from src.shared.embeddings import embed_texts, cosine_similarity, embeddings_enabled  # noqa: E402

    seed = json.loads(Path(args.infile).read_text(encoding="utf-8"))
    types = seed.get("entity_types", [])
    rels = seed.get("relationships", [])

    if args.cqs:
        cqs = _load_cqs_from_file(args.cqs)
    elif args.domain:
        cqs = _load_cqs_from_db(args.grace_root, args.domain)
    else:
        raise SystemExit("[coverage] provide --domain (DB) or --cqs (file)")
    if not cqs:
        raise SystemExit("[coverage] no CQs found")
    cq_texts = [c["text"] for c in cqs]
    type_texts = [_type_text(t) for t in types]
    rel_texts = [_rel_text(r) for r in rels]
    n_cq, n_t = len(cqs), len(types)

    use_embeddings = embeddings_enabled(args.base_url) and not args.lexical
    mode = "embedding" if use_embeddings else "lexical"
    print(f"[coverage] {len(cqs)} CQs, {len(types)} types, {len(rels)} relationships -> mode={mode}")

    # Similarity matrices: rows = CQs, cols = types / rels. Either cosine over
    # embeddings, or Jaccard-style token overlap (no vectors backend needed).
    if use_embeddings:
        try:
            all_vecs = asyncio.run(embed_texts(cq_texts + type_texts + rel_texts, args.base_url))
        except Exception as exc:  # noqa: BLE001 — degrade to lexical, never block the demo
            print(f"[coverage] WARN embeddings failed ({type(exc).__name__}: {exc}); falling back to lexical mode")
            use_embeddings, mode = False, "lexical"
    if use_embeddings:
        vecs = np.array(all_vecs, dtype=float)
        cq_v = vecs[:n_cq]
        type_v = vecs[n_cq:n_cq + n_t]
        rel_v = vecs[n_cq + n_t:]
        type_sims = [cosine_similarity(cq_v[i], type_v) if n_t else np.array([]) for i in range(n_cq)]
        rel_sims = [cosine_similarity(cq_v[i], rel_v) if len(rels) else np.array([]) for i in range(n_cq)]
        threshold = args.threshold
    else:
        type_sims = [_lexical_sims(cq_texts[i], type_texts) for i in range(n_cq)]
        rel_sims = [_lexical_sims(cq_texts[i], rel_texts) for i in range(n_cq)]
        # Token overlap scores are much smaller than cosine scores; use a
        # lexical-appropriate floor unless the operator passed one explicitly.
        threshold = args.threshold if args.threshold != 0.5 else 0.15

    # Coverage the authoring LLM already declared (answerable_cqs) is preserved and
    # counts as coverage — the LLM read the corpus; a similarity score did not.
    authored_type_cov = {t["name"]: set(map(_norm, t.get("answerable_cqs") or [])) for t in types}
    authored_rel_cov = {r["name"]: set(map(_norm, r.get("answerable_cqs") or [])) for r in rels}
    for t in types:
        t["answerable_cqs"] = []
    for r in rels:
        r["answerable_cqs"] = []

    coverage_matrix = []
    covered = 0
    for i, c in enumerate(cqs):
        cov_types, cov_rels = [], []
        for j, t in enumerate(types):
            if _norm(c["text"]) in authored_type_cov[t["name"]]:
                cov_types.append(t["name"])
        for j, r in enumerate(rels):
            if _norm(c["text"]) in authored_rel_cov[r["name"]]:
                cov_rels.append(r["name"])
        if n_t and len(type_sims[i]):
            sims = type_sims[i]
            for j in np.argsort(sims)[::-1][:args.top_k]:
                if sims[j] >= threshold and types[j]["name"] not in cov_types:
                    cov_types.append(types[j]["name"])
        if len(rels) and len(rel_sims[i]):
            sims = rel_sims[i]
            for j in np.argsort(sims)[::-1][:args.top_k]:
                if sims[j] >= threshold and rels[j]["name"] not in cov_rels:
                    cov_rels.append(rels[j]["name"])
        for name in cov_types:
            next(t for t in types if t["name"] == name)["answerable_cqs"].append(c["text"])
        for name in cov_rels:
            next(r for r in rels if r["name"] == name)["answerable_cqs"].append(c["text"])
        if cov_types and cov_rels:
            status = "covered"; covered += 1
        elif cov_types or cov_rels:
            status = "partial"; covered += 1
        else:
            status = "uncovered"
        coverage_matrix.append({
            "cq_id": c["id"][:8], "cq_text": c["text"], "domain": args.domain or "other",
            "covered_by_types": cov_types, "covered_by_relationships": cov_rels,
            "coverage_status": status,
        })

    seed["coverage_matrix"] = coverage_matrix
    qm = seed.get("quality_metrics") or {}
    qm["cq_coverage_rate"] = round(covered / len(cqs), 3)
    qm["cq_coverage_method"] = mode
    seed["quality_metrics"] = qm

    out = args.out or args.infile
    Path(out).write_text(json.dumps(seed, indent=2), encoding="utf-8")
    uncovered = [m["cq_text"] for m in coverage_matrix if m["coverage_status"] == "uncovered"]
    print(f"[coverage] coverage_rate={qm['cq_coverage_rate']}  "
          f"covered/partial={covered}/{len(cqs)}  uncovered={len(uncovered)}")
    for u in uncovered[:10]:
        print(f"  UNCOVERED: {u[:90]}")
    print(f"[coverage] wrote {out} (mode={mode}) — ready for auto_accept.py")


if __name__ == "__main__":
    main()
