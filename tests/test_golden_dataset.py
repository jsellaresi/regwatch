from pathlib import Path

import pytest
from langchain_community.document_loaders import PDFPlumberLoader

from evals.golden_dataset import GOLDEN_CASES
from evals.retrieval_eval import expected_article, expected_regulation
from graph.schemas import VALID_CITATION_RE
from scripts.ingest_regulations import REGULATIONS, split_into_chunks

REPO_ROOT = Path(__file__).resolve().parent.parent
PDF_BY_REGULATION = {name: REPO_ROOT / pdf_path for pdf_path, name, *_ in REGULATIONS}
RISK_LEVELS = {"HIGH", "MEDIUM", "LOW"}


def _expected_refs():
    return [(case["id"], gap["regulation_ref"]) for case in GOLDEN_CASES for gap in case["expected_gaps"]]


def test_case_ids_are_unique_and_every_case_has_an_excerpt():
    ids = [case["id"] for case in GOLDEN_CASES]
    assert len(ids) == len(set(ids))
    assert all(case["document_excerpt"].strip() for case in GOLDEN_CASES)


def test_the_dataset_is_wide_enough_to_mean_something():
    with_gap = [c for c in GOLDEN_CASES if c["expected_gaps"]]
    without_gap = [c for c in GOLDEN_CASES if not c["expected_gaps"]]
    assert len(with_gap) >= 10
    assert len(without_gap) >= 3  # false-positive controls
    covered = {expected_regulation(ref) for _, ref in _expected_refs()}
    assert {"GDPR", "MiFID II", "4AMLD"} <= covered


def test_expected_refs_use_the_citation_format_the_guardrail_enforces_and_a_known_risk_level():
    for case in GOLDEN_CASES:
        for gap in case["expected_gaps"]:
            assert VALID_CITATION_RE.match(gap["regulation_ref"]), (case["id"], gap["regulation_ref"])
            assert gap["risk_level"] in RISK_LEVELS, case["id"]


@pytest.fixture(scope="module")
def articles_in_corpus():
    """Article numbers present in each regulation's real text (as tagged at ingestion)."""
    found = {}
    for name in {expected_regulation(ref) for _, ref in _expected_refs()}:
        chunks = split_into_chunks(PDFPlumberLoader(str(PDF_BY_REGULATION[name])).load())
        found[name] = {n for chunk in chunks for n in chunk.metadata["articles"]}
    return found


def test_every_expected_article_exists_in_the_text_of_its_regulation(articles_in_corpus):
    missing = [
        (case_id, ref) for case_id, ref in _expected_refs()
        if expected_article(ref) not in articles_in_corpus[expected_regulation(ref)]
    ]
    assert not missing, f"labels pointing to an article that is not in the corpus: {missing}"
