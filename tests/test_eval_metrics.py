import inspect

import pytest

from evals import eval_suite
from evals.eval_suite import MIN_PRECISION, MIN_RECALL, article_level, average, compute_metrics, format_results


def _result(case_id, precision, recall, expected, predicted):
    return {"case_id": case_id, "precision": precision, "recall": recall,
            "expected_refs": expected, "predicted_refs": predicted}


RESULTS = [
    _result("gdpr-dpo-001", 1.0, 1.0, ["GDPR Art. 37(1)"], ["GDPR Art. 37(1)"]),
    _result("aml-str-001", 0.5, 1.0, ["4AMLD Art. 33(1)"], ["4AMLD Art. 33(1)", "4AMLD Art. 13"]),
    _result("no-gap-001", 1.0, 1.0, [], []),
]


def test_average_of_a_metric_over_the_cases_and_of_nothing():
    assert average(RESULTS, "precision") == pytest.approx(2.5 / 3)
    assert average([], "precision") == 0.0


def test_the_results_table_has_one_line_per_case_at_article_level_and_the_averages():
    lines = format_results(RESULTS).splitlines()
    assert len(lines) == len(RESULTS) + 2  # header + cases + averages
    assert "GDPR Art. 37 | GDPR Art. 37" in lines[1]
    assert "4AMLD Art. 33 | 4AMLD Art. 13, 4AMLD Art. 33" in lines[2]  # the extra citation is visible
    assert lines[3].rstrip().endswith("- | -")  # a case with no expected gap and no prediction
    assert f"min {MIN_PRECISION}" in lines[-1] and f"min {MIN_RECALL}" in lines[-1]
    assert "average precision 0.83" in lines[-1]


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
