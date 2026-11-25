import pytest
from langchain_anthropic import ChatAnthropic
from config import MODEL_ANALYZER
from evals.golden_dataset import GOLDEN_CASES
from graph.schemas import GapReport, VALID_CITATION_RE
from config import get_langfuse

_llm = None


def _get_llm():
    global _llm
    if _llm is None:
        _llm = ChatAnthropic(model=MODEL_ANALYZER, temperature=0).with_structured_output(GapReport)
    return _llm


def compute_metrics(predicted_refs: set[str], expected_refs: set[str]) -> tuple[float, float]:
    """Precision and recall for one case. Predicting nothing is only a perfect
    precision when there was nothing to find; otherwise it scores 0, so a model
    that returns no gaps can't inflate the average."""
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


@pytest.fixture(scope="module")
def results() -> list[dict]:
    return [run_single_eval(c) for c in GOLDEN_CASES]


class TestPromptPromotion:

    def test_average_precision_above_threshold(self, results):
        avg_precision = sum(r["precision"] for r in results) / len(results)
        assert avg_precision >= 0.85, (
            f"Precisión media {avg_precision:.2f} por debajo del umbral 0.85. "
            "No promover el prompt a producción."
        )

    def test_average_recall_above_threshold(self, results):
        avg_recall = sum(r["recall"] for r in results) / len(results)
        assert avg_recall >= 0.80, (
            f"Recall medio {avg_recall:.2f} por debajo del umbral 0.80."
        )

    def test_no_hallucinated_citations(self, results):
        for r in results:
            for ref in r["predicted_refs"]:
                assert VALID_CITATION_RE.match(ref), f"Cita con formato incorrecto: '{ref}'"
