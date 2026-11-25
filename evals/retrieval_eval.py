"""Retrieval quality eval: does the pipeline's own retrieval + rerank surface the
regulation (and the article) a golden case is expected to cite?

This is the part of the system the analysis depends on most: an article that is
never retrieved is a gap that can never be detected (ADR-0003/ADR-0004). It needs
the corpus ingested in Postgres and real embeddings, so it runs in the eval gate,
not in the unit-test suite.
"""
import re
from statistics import mean

from graph.nodes import rerank, retrieve_regulations


def expected_regulation(ref: str) -> str:
    """'GDPR Art. 5(1)(e)' -> 'GDPR' (the name stored in the chunk metadata)."""
    return ref.split(" Art.")[0].strip()


def expected_article(ref: str) -> int | None:
    match = re.search(r"Art\. (\d+)", ref)
    return int(match.group(1)) if match else None


def score_retrieval(retrieved: list[dict], ref: str) -> dict:
    """regulation_hit: some retrieved chunk belongs to the expected regulation.
    article_hit: the chunk that opens the expected article ("Artículo N" at the
    start of a line) is among the retrieved ones. A chunk that merely continues a
    long article does not count, so article_hit is a conservative measure."""
    regulation = expected_regulation(ref)
    article = expected_article(ref)
    from_regulation = [c for c in retrieved if c.get("regulation") == regulation]
    article_hit = article is not None and any(
        re.search(rf"(?m)^\s*Art[ií]culo\s+{article}\b", c.get("content", "")) for c in from_regulation
    )
    return {"regulation_hit": bool(from_regulation), "article_hit": article_hit}


def _rate(rows: list[dict], stage: str, key: str) -> float:
    return mean(1.0 if row[stage][key] else 0.0 for row in rows) if rows else 0.0


def evaluate_retrieval(cases: list[dict], retrieve=retrieve_regulations, rerank_fn=rerank) -> dict:
    """Run retrieval then rerank for every case that expects at least one gap.
    `before` is the candidate set handed to the reranker, `after` the final top-N
    the analyzer actually sees; thresholds apply to `after`."""
    rows = []
    for case in cases:
        refs = [g["regulation_ref"] for g in case["expected_gaps"]]
        if not refs:
            continue
        state = {"extracted_text": case["document_excerpt"]}
        candidates = retrieve(state)["retrieved_regulations"]
        top = rerank_fn({**state, "retrieved_regulations": candidates})["retrieved_regulations"]
        for ref in refs:
            rows.append({
                "case_id": case["id"],
                "ref": ref,
                "candidates": len(candidates),
                "final": len(top),
                "before": score_retrieval(candidates, ref),
                "after": score_retrieval(top, ref),
            })
    return {
        "rows": rows,
        "regulation_hit_rate": _rate(rows, "after", "regulation_hit"),
        "article_hit_rate": _rate(rows, "after", "article_hit"),
        "regulation_hit_rate_before_rerank": _rate(rows, "before", "regulation_hit"),
        "article_hit_rate_before_rerank": _rate(rows, "before", "article_hit"),
    }


def format_report(report: dict) -> str:
    lines = [f"{'case':<24}{'expected ref':<22}{'cand.':>6}{'top':>5}  reg(before>after)  art(before>after)"]
    for row in report["rows"]:
        reg = f"{row['before']['regulation_hit']:d}>{row['after']['regulation_hit']:d}"
        art = f"{row['before']['article_hit']:d}>{row['after']['article_hit']:d}"
        lines.append(f"{row['case_id']:<24}{row['ref']:<22}{row['candidates']:>6}{row['final']:>5}  {reg:<18} {art}")
    lines.append(
        f"regulation hit rate: {report['regulation_hit_rate']:.2f} "
        f"(before rerank {report['regulation_hit_rate_before_rerank']:.2f}) | "
        f"article hit rate: {report['article_hit_rate']:.2f} "
        f"(before rerank {report['article_hit_rate_before_rerank']:.2f})"
    )
    return "\n".join(lines)
