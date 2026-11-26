import inspect

import pytest

from evals import eval_suite
from evals.eval_suite import article_level, compute_metrics


@pytest.mark.parametrize(
    "ref, expected",
    [
        ("GDPR Art. 5(1)(e)", "GDPR Art. 5"),
        ("GDPR Art. 35(3)", "GDPR Art. 35"),
        ("MiFID II Art. 23", "MiFID II Art. 23"),
        ("4AMLD Art. 13(1)(b) ", "4AMLD Art. 13"),
        ("A", "A"),
    ],
)
def test_article_level_drops_the_paragraph_suffix(ref, expected):
    assert article_level(ref) == expected


def test_a_different_paragraph_of_the_right_article_is_a_hit():
    assert compute_metrics({"GDPR Art. 35(3)"}, {"GDPR Art. 35(1)"}) == (1.0, 1.0)


def test_several_paragraphs_of_one_article_count_once():
    assert compute_metrics({"GDPR Art. 5(1)(e)", "GDPR Art. 5(1)(f)"}, {"GDPR Art. 5(1)(e)"}) == (1.0, 1.0)


def test_a_different_article_is_still_a_miss():
    assert compute_metrics({"GDPR Art. 6(1)"}, {"GDPR Art. 5(1)(e)"}) == (0.0, 0.0)


@pytest.mark.parametrize(
    "predicted, expected, precision, recall",
    [
        ({"A"}, {"A"}, 1.0, 1.0),
        ({"A", "B"}, {"A"}, 0.5, 1.0),
        ({"A"}, {"A", "B"}, 1.0, 0.5),
        (set(), {"A"}, 0.0, 0.0),
        (set(), set(), 1.0, 1.0),
        ({"A"}, set(), 0.0, 1.0),
    ],
)
def test_compute_metrics(predicted, expected, precision, recall):
    assert compute_metrics(predicted, expected) == (precision, recall)


def test_predicting_nothing_no_longer_inflates_average_precision():
    cases = [({"A"}, {"A"}), (set(), {"B"}), (set(), {"C"})]
    avg = sum(compute_metrics(p, e)[0] for p, e in cases) / len(cases)
    assert avg == pytest.approx(1 / 3)


def test_threshold_tests_share_one_evaluation_run():
    # The three threshold tests used to each call run_single_eval over the whole
    # dataset (3x the LLM calls); they must now take the shared `results` fixture.
    for name in ("test_average_precision_above_threshold",
                 "test_average_recall_above_threshold",
                 "test_no_hallucinated_citations"):
        method = getattr(eval_suite.TestPromptPromotion, name)
        assert "results" in inspect.signature(method).parameters
        assert "run_single_eval" not in inspect.getsource(method)
