import re

import pytest
from langchain_anthropic import ChatAnthropic
from config import MODEL_ANALYZER
from evals.golden_dataset import GOLDEN_CASES
from graph.schemas import GapReport, VALID_CITATION_RE
from config import get_langfuse

MIN_PRECISION = 0.85
MIN_RECALL = 0.80

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model=MODEL_ANALYZER).with_structured_output(GapReport)
    return _llm


def article_level(ref: str) -> str:
    """'GDPR Art. 5(1)(e)' -> 'GDPR Art. 5'. A citation counts when it names the right
    article; which paragraph of it is cited is not scored (the retrieval eval is
    article-level too), so 'Art. 35(1)' and 'Art. 35(3)' are the same hit."""
    return re.sub(r"(\([0-9a-z]+\))+$", "", ref.strip())


def compute_metrics(predicted_refs: set[str], expected_refs: set[str]) -> tuple[float, float]:
    """Precision and recall for one case, comparing citations at article level.
    Predicting nothing is only a perfect precision when there was nothing to find;
    otherwise it scores 0, so a model that returns no gaps can't inflate the average."""
    predicted_refs = {article_level(r) for r in predicted_refs}
    expected_refs = {article_level(r) for r in expected_refs}
    tp = len(predicted_refs & expected_refs)
    fp = len(predicted_refs - expected_refs)
    fn = len(expected_refs - predicted_refs)

    if tp + fp > 0:
        precision = tp / (tp + fp)
    else:
        precision = 1.0 if not expected_refs else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 1.0
    return precision, recall


def run_single_eval(case: dict) -> dict:
    prompt_obj = get_langfuse().get_prompt("compliance-analyzer", label="staging", cache_ttl_seconds=0)
    report: GapReport = _get_llm().invoke(
        f"{prompt_obj.prompt}\n\nDocumento: {case['document_excerpt']}"
    )

    predicted_refs = {g.regulation_ref for g in report.gaps}
    expected_refs = {g["regulation_ref"] for g in case["expected_gaps"]}

    precision, recall = compute_metrics(predicted_refs, expected_refs)

    return {
        "case_id": case["id"],
        "precision": precision,
        "recall": recall,
        "predicted_refs": list(predicted_refs),
        "expected_refs": list(expected_refs),
    }


def average(results: list[dict], key: str) -> float:
    return sum(r[key] for r in results) / len(results) if results else 0.0


def format_results(results: list[dict]) -> str:
    """One line per golden case (expected vs predicted, at article level) plus the averages
    the thresholds apply to, so a failed gate shows which cases the model read differently."""

    def refs(values) -> str:
        return ", ".join(sorted({article_level(v) for v in values})) or "-"

    lines = [f"{'case':<32}{'prec':>5}{'rec':>6}  expected | predicted"]
    for r in results:
        lines.append(
            f"{r['case_id']:<32}{r['precision']:>5.2f}{r['recall']:>6.2f}  "
            f"{refs(r['expected_refs'])} | {refs(r['predicted_refs'])}"
        )
    lines.append(
        f"average precision {average(results, 'precision'):.2f} (min {MIN_PRECISION}) | "
        f"average recall {average(results, 'recall'):.2f} (min {MIN_RECALL})"
    )
    return "\n".join(lines)


@pytest.fixture(scope="module")
def results() -> list[dict]:
    evaluated = [run_single_eval(c) for c in GOLDEN_CASES]
    print("\n" + format_results(evaluated))
    return evaluated


class TestPromptPromotion:

    def test_average_precision_above_threshold(self, results):
        avg_precision = average(results, "precision")
        assert avg_precision >= MIN_PRECISION, (
            f"Precisión media {avg_precision:.2f} por debajo del umbral {MIN_PRECISION}. "
            f"No promover el prompt a producción.\n{format_results(results)}"
        )

    def test_average_recall_above_threshold(self, results):
        avg_recall = average(results, "recall")
        assert avg_recall >= MIN_RECALL, (
            f"Recall medio {avg_recall:.2f} por debajo del umbral {MIN_RECALL}.\n{format_results(results)}"
        )

    def test_no_hallucinated_citations(self, results):
        for r in results:
            for ref in r["predicted_refs"]:
                assert VALID_CITATION_RE.match(ref), (
                    f"Cita con formato incorrecto: '{ref}' (caso {r['case_id']})\n{format_results(results)}"
                )
