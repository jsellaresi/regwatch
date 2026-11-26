import pytest

from evals.retrieval_eval import (
    evaluate_retrieval,
    expected_article,
    expected_regulation,
    format_report,
    score_retrieval,
)


@pytest.mark.parametrize(
    "ref, regulation, article",
    [
        ("GDPR Art. 5(1)(e)", "GDPR", 5),
        ("MiFID II Art. 23", "MiFID II", 23),
        ("4AMLD Art. 11", "4AMLD", 11),
        ("GDPR", "GDPR", None),
    ],
)
def test_expected_regulation_and_article(ref, regulation, article):
    assert expected_regulation(ref) == regulation
    assert expected_article(ref) == article


def _chunk(regulation, content):
    return {"regulation": regulation, "content": content}


def test_regulation_hit_requires_a_chunk_of_that_regulation():
    chunks = [_chunk("MiFID II", "Artículo 23\nConflictos de intereses")]
    assert score_retrieval(chunks, "GDPR Art. 5(1)(e)")["regulation_hit"] is False
    assert score_retrieval(chunks, "MiFID II Art. 23")["regulation_hit"] is True


def test_article_hit_needs_the_chunk_that_opens_the_expected_article():
    opens = _chunk("GDPR", "Artículo 5\nPrincipios relativos al tratamiento")
    assert score_retrieval([opens], "GDPR Art. 5(1)(e)")["article_hit"] is True


def test_article_hit_ignores_cross_references_and_other_article_numbers():
    cross_reference = _chunk("GDPR", "como dispone el Artículo 5 del presente Reglamento, el responsable")
    other = _chunk("GDPR", "Artículo 50\nCooperación internacional")
    lowercase = _chunk("GDPR", "conforme al artículo 5\ndel Reglamento")
    result = score_retrieval([cross_reference, other, lowercase], "GDPR Art. 5(1)(e)")
    assert result == {"regulation_hit": True, "article_hit": False}


def test_article_hit_does_not_count_the_right_number_in_the_wrong_regulation():
    chunks = [_chunk("4AMLD", "Artículo 5\nOtra cosa")]
    assert score_retrieval(chunks, "GDPR Art. 5(1)(e)")["article_hit"] is False


CASES = [
    {"id": "c1", "document_excerpt": "retención indefinida", "expected_gaps": [{"regulation_ref": "GDPR Art. 5(1)(e)"}]},
    {"id": "c2", "document_excerpt": "conflictos", "expected_gaps": [{"regulation_ref": "MiFID II Art. 23"}]},
    {"id": "clean", "document_excerpt": "todo correcto", "expected_gaps": []},
]


def _retrieve(state):
    pool = {
        "retención indefinida": [_chunk("GDPR", "Artículo 5\nPrincipios"), _chunk("GDPR", "Artículo 17\nSupresión")],
        "conflictos": [_chunk("MiFID II", "Artículo 16\nOrganización"), _chunk("GDPR", "Artículo 5\nx")],
    }
    return {"retrieved_regulations": pool[state["extracted_text"]]}


def _keep_first(state):
    return {"retrieved_regulations": state["retrieved_regulations"][:1]}


def test_evaluate_retrieval_scores_before_and_after_rerank_and_skips_clean_cases():
    report = evaluate_retrieval(CASES, retrieve=_retrieve, rerank_fn=_keep_first)
    assert [row["case_id"] for row in report["rows"]] == ["c1", "c2"]
    # c1: GDPR Art. 5 is the top chunk -> hit. c2: the MiFID II chunk is Art. 16, not 23 -> regulation hit, no article hit
    assert report["regulation_hit_rate"] == 1.0
    assert report["article_hit_rate"] == 0.5
    assert report["rows"][0]["candidates"] == 2 and report["rows"][0]["final"] == 1


def test_a_reranker_that_drops_the_right_chunk_lowers_the_final_rate_but_not_the_before_rate():
    def keep_last(state):
        return {"retrieved_regulations": state["retrieved_regulations"][-1:]}

    report = evaluate_retrieval(CASES, retrieve=_retrieve, rerank_fn=keep_last)
    assert report["article_hit_rate_before_rerank"] == 0.5
    assert report["article_hit_rate"] == 0.0
    assert report["regulation_hit_rate_before_rerank"] == 1.0
    assert report["regulation_hit_rate"] == 0.5


def test_no_evaluable_cases_gives_zero_rates_not_a_crash():
    report = evaluate_retrieval([CASES[2]], retrieve=_retrieve, rerank_fn=_keep_first)
    assert report["rows"] == [] and report["regulation_hit_rate"] == 0.0
    assert "regulation hit rate" in format_report(report)


def test_a_continuation_chunk_tagged_with_the_article_counts_as_an_article_hit():
    # The cited paragraph usually sits in a later chunk of a long article, which has no header.
    continuation = {"regulation": "GDPR", "content": "e) mantenidos durante no más tiempo", "articles": [5]}
    assert score_retrieval([continuation], "GDPR Art. 5(1)(e)")["article_hit"] is True


def test_a_chunk_tagged_with_another_article_is_not_a_hit():
    other = {"regulation": "GDPR", "content": "texto", "articles": [6]}
    assert score_retrieval([other], "GDPR Art. 5(1)(e)")["article_hit"] is False


def test_the_articles_tag_does_not_cross_regulations():
    chunk = {"regulation": "4AMLD", "content": "texto", "articles": [5]}
    assert score_retrieval([chunk], "GDPR Art. 5(1)(e)") == {"regulation_hit": False, "article_hit": False}


def test_long_case_ids_never_run_into_the_next_column():
    hit = {"regulation_hit": True, "article_hit": True}
    row = {"case_id": "gdpr-consent-withdrawal-001", "ref": "GDPR Art. 7(3)", "candidates": 37,
           "final": 8, "before": hit, "after": hit}
    report = {"rows": [row], "regulation_hit_rate": 1.0, "article_hit_rate": 1.0,
              "regulation_hit_rate_before_rerank": 1.0, "article_hit_rate_before_rerank": 1.0}
    header, line = format_report(report).splitlines()[:2]
    assert "gdpr-consent-withdrawal-001  GDPR Art. 7(3)" in line
    assert header.index("expected ref") == line.index("GDPR Art. 7(3)")
