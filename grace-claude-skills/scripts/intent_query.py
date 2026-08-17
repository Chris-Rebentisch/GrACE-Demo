#!/usr/bin/env python3
"""Intent harness — READ/EXTRACT tool. Three modes; all read-only, heat-free.

  --facts "<name substring>|*"        prepare-phase queue: the facts to elicit (any type)
  --similar "<statement>" --applies-when "<scope>"   canonicalization: near-duplicate principles
  --ask "<a novel decision>"          extraction: top-K principles + precedent + rejected paths
                                      to compose a human-inspired resolution

Embodies the extraction rule (D-int-14): retrieve top-K, select using ``applies_when``, never
trust rank #1. Embeds queries over statement+applies_when (D-int-5). Embeddings optional (keyword fallback when disabled).

  python3 intent_query.py --ask "We're licensing exclusively to a much larger partner who runs
                                 all the regulatory work — who should bear the compliance cost?"
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from _common import add_grace_to_path, route_logs_to_stderr  # noqa: E402

# high-stakes obligation types — a wrong/unexamined why is expensive on these (prepare queue)
_HIGH_STAKES = ("payment", "governance", "indemnification", "non_compete", "exclusivity",
                "restriction", "warranty", "change_control")


# Meta / intent-layer types are never "facts to elicit".
_NON_FACT_TYPES = {
    "Decision_Principle", "Decision_Rationale", "Counterfactual", "Mandatory_Provision",
    "Extraction_Event", "Document_Chunk", "Query_Event", "Response_Event", "Image_Asset",
    "Bridge_Entity", "Cross_System_Reference",
}


def _label(row_labels) -> str:
    labs = [x for x in (row_labels or []) if x]
    return labs[0] if labs else "?"


async def _facts(needle: str, ollama: str, full: bool = False) -> None:
    """Prepare-phase queue: fact vertices (any ontology type) whose name matches ``needle``
    ("*" or "" = all), with how much intent is already captured on each. Generic over the
    active ontology — no assumption about Agreement/Obligation types."""
    add_grace_to_path()
    from src.graph.arcade_client import get_arcade_client
    from src.graph.cypher_utils import escape_cypher_string
    c = get_arcade_client()
    n = escape_cypher_string("" if needle in ("*", "all") else needle).lower()
    where = f"WHERE o.name IS NOT NULL AND toLower(o.name) CONTAINS '{n}'" if n else "WHERE o.name IS NOT NULL"
    rows = (await c.execute_cypher(
        f"MATCH (o) {where} "
        "OPTIONAL MATCH (o)<-[:justifies]-(r:Decision_Rationale) "
        "OPTIONAL MATCH (o)<-[:explains]-(p:Decision_Principle) "
        "OPTIONAL MATCH (o)-[e]-() "
        "RETURN o.grace_id AS gid, labels(o) AS t, o.name AS name, "
        "count(DISTINCT r) + count(DISTINCT p) AS has_intent, count(DISTINCT e) AS degree "
        "ORDER BY degree DESC LIMIT 200"))["result"]
    rows = [r for r in rows if _label(r["t"]) not in _NON_FACT_TYPES and r.get("gid")]
    await c.aclose()
    if not rows:
        print("No facts found. Run graph extraction first (grace-graph-extraction)."); return
    # High-stakes proxy without a domain vocabulary: the most-connected facts first,
    # facts that already have a captured why last.
    queue = sorted(rows, key=lambda r: (r["has_intent"] > 0, -r["degree"]))
    print("Facts to elicit (★ = highly connected / load-bearing, ✓ = already has a captured why):\n")
    for r in queue[:60]:
        star = "★" if r["degree"] >= 3 else " "
        seen = "✓" if r["has_intent"] else " "
        gid = r["gid"] if full else r["gid"][:8]
        print(f"  {star}{seen} [{_label(r['t']):<20}] {gid}  {r['name'][:80]}")
    print("\nNext: `intent_query.py --fact <gid-prefix>` to see one fact verbatim before asking why.")


async def _fact(gid: str, ollama: str) -> None:
    """One fact's verbatim properties + its neighborhood + any captured intent — for elicitation."""
    add_grace_to_path()
    from src.graph.arcade_client import get_arcade_client
    from src.graph.cypher_utils import escape_cypher_string
    c = get_arcade_client()
    g = escape_cypher_string(gid)
    o = (await c.execute_cypher(
        f"MATCH (o) WHERE o.grace_id STARTS WITH '{g}' RETURN o, labels(o) AS t LIMIT 1"))["result"]
    if not o:
        print(f"No fact found for {gid}"); await c.aclose(); return
    node = o[0]["o"] if isinstance(o[0].get("o"), dict) else o[0]
    label = _label(o[0].get("t"))
    full_gid = node.get("grace_id", gid)
    fg = escape_cypher_string(full_gid)
    nbrs = (await c.execute_cypher(
        f"MATCH (o {{grace_id:'{fg}'}})-[e]-(x) WHERE x.name IS NOT NULL "
        "RETURN type(e) AS rel, labels(x) AS t, x.name AS name, "
        "CASE WHEN startNode(e) = o THEN 'out' ELSE 'in' END AS dir LIMIT 40"))["result"]
    intent = (await c.execute_cypher(
        f"MATCH (o {{grace_id:'{fg}'}}) "
        "OPTIONAL MATCH (r:Decision_Rationale)-[:justifies]->(o) "
        "OPTIONAL MATCH (p:Decision_Principle)-[:explains]->(o) "
        "OPTIONAL MATCH (cf:Counterfactual)-[:rejected_alternative_to]->(o) "
        "OPTIONAL MATCH (mp:Mandatory_Provision)-[:compels]->(o) "
        "RETURN collect(DISTINCT r.name) AS rationales, collect(DISTINCT p.name) AS principles, "
        "collect(DISTINCT cf.name) AS counterfactuals, collect(DISTINCT mp.name) AS compelled"))["result"][0]
    await c.aclose()
    print(f"TYPE: {label}   GRACE_ID: {full_gid}")
    print(f"NAME: {node.get('name')}\n")
    print("VERBATIM PROPERTIES:")
    for k, v in sorted(node.items()):
        if k.startswith("_") or k.startswith("@") or k in ("grace_id", "name") or v in (None, "", [], {}):
            continue
        print(f"  {k}: {v}")
    if nbrs:
        print("\nNEIGHBORHOOD:")
        for nb in nbrs:
            arrow = "->" if nb.get("dir") == "out" else "<-"
            print(f"  {arrow} [{nb['rel']}] {_label(nb.get('t'))} \"{nb.get('name')}\"")
    has = lambda xs: [x for x in xs if x]
    print("\nAlready-captured intent on this fact:")
    print(f"  rationales:      {has(intent['rationales']) or '(none — elicit a why)'}")
    print(f"  principles:      {has(intent['principles']) or '(none)'}")
    print(f"  counterfactuals: {has(intent['counterfactuals']) or '(none)'}")
    print(f"  compelled-by:    {has(intent['compelled']) or '(none — check if mandatory)'}")


async def _similar(statement: str, applies_when: str, ollama: str) -> None:
    add_grace_to_path()
    from src.graph.arcade_client import get_arcade_client
    from src.shared.embeddings import embed_texts, embeddings_enabled
    from src.extraction.intent_writer import find_similar_principles
    if not embeddings_enabled(ollama):
        print("Embeddings are disabled — cannot rank similar principles by vector. "
              "List existing principles with `--facts` / Cypher and let the human judge reuse.")
        return
    c = get_arcade_client()
    qv = (await embed_texts([f"{statement} Applies when: {applies_when}"], base_url=ollama))[0]
    # P4: surface near-PARENTS too, not just duplicates — tier the output (low floor 0.62).
    hits = await find_similar_principles(c, qv, top_k=8, threshold=0.62)
    await c.aclose()
    if not hits:
        print("No existing principle is related — this is a NEW principle."); return
    dup = [h for h in hits if h["similarity"] >= 0.93]
    strong = [h for h in hits if 0.80 <= h["similarity"] < 0.93]
    related = [h for h in hits if 0.62 <= h["similarity"] < 0.80]
    if dup:
        print("LIKELY DUPLICATE — reuse this principle (do not re-author):")
        for h in dup: print(f"  [{h['similarity']:.3f}] {h['name']}")
    if strong:
        print("STRONG OVERLAP — confirm reuse with the human before authoring new:")
        for h in strong: print(f"  [{h['similarity']:.3f}] {h['name']}")
    if related:
        print("RELATED — consider `specializes` (is your principle a CHILD of one of these?). Human judges:")
        for h in related: print(f"  [{h['similarity']:.3f}] {h['name']}")
    print("\nNote: at this range similarity is a weak parent signal — the human decides reuse vs specialize vs new.")


async def _ask(question: str, top_k: int, ollama: str) -> None:
    add_grace_to_path()
    from src.graph.arcade_client import get_arcade_client
    from src.shared.embeddings import embed_texts, embeddings_enabled
    from src.graph.cypher_utils import escape_cypher_string
    import numpy as np
    c = get_arcade_client()
    prows = (await c.execute_cypher(
        "MATCH (p:Decision_Principle) RETURN p.name AS name, p.statement AS s, "
        "p.applies_when AS w, p.certainty_band AS band"))["result"]
    if not prows:
        print(f'QUESTION: "{question}"\n\nNo captured principles yet — run intent elicitation first.')
        await c.aclose(); return
    if embeddings_enabled(ollama):
        pemb = await embed_texts([f"{r['s']} Applies when: {r['w']}" for r in prows], base_url=ollama)
        qv = np.array((await embed_texts([question], base_url=ollama))[0])
        cos = lambda e: float(qv @ np.array(e) / (np.linalg.norm(qv) * np.linalg.norm(e)))
        ranked = sorted(((cos(e), r) for e, r in zip(pemb, prows)), key=lambda x: -x[0])[:top_k]
    else:
        # No vectors backend: rank by token overlap between the question and each
        # principle's statement + applies_when. The human (or the operating LLM)
        # selects by applies_when anyway — rank is a hint, not a verdict.
        def _tok(t: str) -> set[str]:
            return {w.strip(".,;:?!()").lower() for w in (t or "").split() if len(w) > 2}
        qt = _tok(question)
        def _lex(r: dict) -> float:
            pt = _tok(f"{r['s']} {r['w']}")
            return len(qt & pt) / len(qt) if qt else 0.0
        ranked = sorted(((_lex(r), r) for r in prows), key=lambda x: -x[0])[:top_k]
        print("(embeddings disabled — ranked by keyword overlap)")

    print(f'QUESTION: "{question}"\n')
    print(f"Top {top_k} captured principles (select by applies_when — do NOT trust rank #1):\n")
    for score, p in ranked:
        esc = escape_cypher_string(p["name"])
        rat = (await c.execute_cypher(
            f"MATCH (r:Decision_Rationale)-[:applies_principle]->(:Decision_Principle {{name:'{esc}'}}) "
            "RETURN r.name AS name, r.summary AS summary, r.leverage AS leverage LIMIT 1"))["result"]
        contracts = (await c.execute_cypher(
            f"MATCH (:Decision_Principle {{name:'{esc}'}})-[:explains]->(o:Obligation)"
            "<-[:has_obligation]-(a:Agreement) RETURN DISTINCT a.name AS name"))["result"]
        cfs = (await c.execute_cypher(
            f"MATCH (:Decision_Principle {{name:'{esc}'}})-[:explains]->(f)"
            "<-[:rejected_alternative_to]-(cf:Counterfactual) "
            "RETURN cf.demanded AS demanded, cf.why_rejected AS why LIMIT 1"))["result"]
        print(f"  [{score:.3f}] {p['name']}  (applies_when scope below; certainty {p['band']})")
        print(f"     \"{p['s']}\"")
        if rat:
            print(f"     precedent: {rat[0]['name']} — {rat[0]['summary'][:120]}")
            if rat[0]["leverage"]: print(f"     leverage : {rat[0]['leverage']}")
        if contracts:
            print(f"     drawn from: {', '.join(x['name'][:38] for x in contracts[:3])}")
        if cfs:
            print(f"     already-rejected: {cfs[0]['demanded'][:90]} ({cfs[0]['why'][:60]})")
        print()
    await c.aclose()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--facts", help="list facts to elicit: name substring, or '*' for all (any ontology type)")
    ap.add_argument("--full", action="store_true", help="with --facts: print verbatim clauses + full grace_ids")
    ap.add_argument("--fact", help="one fact's verbatim text + neighborhood + captured intent (grace_id prefix)")
    ap.add_argument("--similar", help="statement of a proposed principle to canonicalize")
    ap.add_argument("--applies-when", default="", help="scope of the proposed principle (with --similar)")
    ap.add_argument("--ask", help="a novel decision to resolve from captured intent")
    ap.add_argument("--top-k", type=int, default=4)
    ap.add_argument("--ollama", default="http://localhost:11434")
    args = ap.parse_args()
    route_logs_to_stderr()
    if args.facts:
        asyncio.run(_facts(args.facts, args.ollama, full=args.full))
    elif args.fact:
        asyncio.run(_fact(args.fact, args.ollama))
    elif args.similar:
        asyncio.run(_similar(args.similar, args.applies_when, args.ollama))
    elif args.ask:
        asyncio.run(_ask(args.ask, args.top_k, args.ollama))
    else:
        ap.error("one of --facts / --fact / --similar / --ask is required")


if __name__ == "__main__":
    main()
