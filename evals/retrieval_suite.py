"""Retrieval gate: needs the corpus ingested in Postgres (DATABASE_URL), OPENAI_API_KEY
for query embeddings and a reranker (COHERE_API_KEY, or the local BGE model).

The thresholds are PROVISIONAL: they have not been calibrated against a real run yet.
Override them with RETRIEVAL_MIN_REGULATION_HIT / RETRIEVAL_MIN_ARTICLE_HIT once a first
run shows what the system actually achieves.
"""
import os

import pytest

from evals.golden_dataset import GOLDEN_CASES
from evals.retrieval_eval import evaluate_retrieval, format_report

MIN_REGULATION_HIT = float(os.getenv("RETRIEVAL_MIN_REGULATION_HIT", "0.75"))
MIN_ARTICLE_HIT = float(os.getenv("RETRIEVAL_MIN_ARTICLE_HIT", "0.5"))


@pytest.fixture(scope="module")
def report() -> dict:
    result = evaluate_retrieval(GOLDEN_CASES)
    print("\n" + format_report(result))
    return result


class TestRetrievalQuality:

    def test_corpus_is_not_empty_and_cases_were_evaluated(self, report):
        assert report["rows"], "no golden case with expected gaps was evaluated"
        assert all(row["candidates"] > 0 for row in report["rows"]), (
            "retrieval returned nothing: is the regulation corpus ingested?\n" + format_report(report)
        )

    def test_expected_regulation_is_retrieved(self, report):
        assert report["regulation_hit_rate"] >= MIN_REGULATION_HIT, (
            f"regulation hit rate {report['regulation_hit_rate']:.2f} < {MIN_REGULATION_HIT}\n" + format_report(report)
        )

    def test_expected_article_is_retrieved(self, report):
        assert report["article_hit_rate"] >= MIN_ARTICLE_HIT, (
            f"article hit rate {report['article_hit_rate']:.2f} < {MIN_ARTICLE_HIT}\n" + format_report(report)
        )
