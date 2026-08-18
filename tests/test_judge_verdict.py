"""Regression tests for fix 11.

Before this fix, agent_judge.py:
1. Never gave the judge the retrieved regulations — only the gap report and
   a 2000-char excerpt of the source document. It was asked to score
   citation_quality ("are citations verifiable?") with no legal text to
   verify them against, so it could only judge from parametric memory.
2. Asked the LLM to compute overall_score (an average of 3 numbers) and
   approved (a >= 7.0 comparison) itself, rather than in Python.

graph.nodes.agent_judge is inside the `graph` package, so importing it here
does pay the ~15-20s LangChain/torch import cost (once per test session,
cached afterwards) — accepted, since verifying the actual wired-up function
matters more than avoiding that cost for this one.
"""

import pytest

from graph.nodes.agent_judge import JUDGE_SYSTEM, compute_judge_verdict
from graph.schemas import JudgeSubScores


@pytest.mark.parametrize(
    "legal_accuracy,citation_quality,actionability,expected_overall,expected_approved",
    [
        (10, 10, 10, 10.0, True),
        (0, 0, 0, 0.0, False),
        (7, 7, 7, 7.0, True),  # exact threshold: must approve, not just "close enough"
        (6, 7, 7, pytest.approx(6.6666666, rel=1e-4), False),  # just under threshold
        (8, 6, 8, pytest.approx(7.3333333, rel=1e-4), True),
    ],
)
def test_compute_judge_verdict(legal_accuracy, citation_quality, actionability, expected_overall, expected_approved):
    overall_score, approved = compute_judge_verdict(legal_accuracy, citation_quality, actionability)
    assert overall_score == expected_overall
    assert approved is expected_approved


def test_compute_judge_verdict_respects_custom_threshold():
    overall_score, approved = compute_judge_verdict(5, 5, 5, threshold=4.0)
    assert overall_score == 5.0
    assert approved is True


def test_llm_structured_output_schema_excludes_overall_score_and_approved():
    # Regression guard: these two must stay computed in Python, not
    # re-delegated to the LLM's structured output.
    fields = JudgeSubScores.model_fields
    assert "overall_score" not in fields
    assert "approved" not in fields
    assert set(fields) == {"legal_accuracy", "citation_quality", "actionability", "critical_issues"}


def test_judge_system_prompt_no_longer_asks_llm_to_compute_the_verdict():
    assert "promedio" not in JUDGE_SYSTEM
    assert ">= 7.0" not in JUDGE_SYSTEM


def test_judge_system_prompt_tells_llm_to_verify_citations_against_provided_text():
    assert "texto de las regulaciones" in JUDGE_SYSTEM
