"""Unit tests for build_retry_feedback (fix 3).

The bug this fixes: analyze_compliance's retry path resent the exact same
HumanMessage regardless of *why* the previous attempt was rejected by the
output guardrail or the judge. With the global LLM cache enabled
(config.init_llm_cache), an unchanged prompt is a cache
hit on the same (failing) response — so the retry loop could never actually
correct anything. build_retry_feedback renders the guardrail/judge feedback
into a prompt block that changes the input (and therefore the cache key) on
a genuine retry, while staying empty on a fresh run.

Note: `import graph.nodes.analyze_compliance as m` binds `m` to the
node *function* of that name, not the module — graph/nodes/__init__.py's
`from graph.nodes.analyze_compliance import analyze_compliance` shadows the
submodule attribute on the `graph.nodes` package with the function object
(a standard Python gotcha whenever a module and one of its own members
share a name). Importing the specific name directly avoids it.
"""

from graph.nodes.analyze_compliance import build_retry_feedback


def test_fresh_run_has_no_feedback():
    # A first-ever call never has guardrail_reason/judge_scores in state at all.
    assert build_retry_feedback({}) == ""


def test_empty_guardrail_reason_and_no_judge_scores_yield_no_feedback():
    # output_guardrail explicitly resets guardrail_reason to "" on a pass —
    # that must not be mistaken for "there was feedback".
    state = {"guardrail_reason": "", "judge_scores": {}}
    assert build_retry_feedback(state) == ""


def test_guardrail_rejection_is_rendered():
    state = {"guardrail_reason": "Cita inválida: 'GDPR Art. 5(1)e'"}
    result = build_retry_feedback(state)
    assert result.startswith("## Correcciones requeridas")
    assert "Guardrail de salida: Cita inválida: 'GDPR Art. 5(1)e'" in result


def test_judge_critical_issues_are_rendered():
    state = {"judge_scores": {"critical_issues": ["Falta remediación concreta", "Cita no verificable"]}}
    result = build_retry_feedback(state)
    assert "Judge: Falta remediación concreta" in result
    assert "Judge: Cita no verificable" in result


def test_judge_scores_without_critical_issues_key_is_handled():
    state = {"judge_scores": {"overall_score": 5.0}}
    assert build_retry_feedback(state) == ""


def test_both_guardrail_and_judge_feedback_combine():
    state = {
        "guardrail_reason": "Cita inválida",
        "judge_scores": {"critical_issues": ["Falta remediación"]},
    }
    result = build_retry_feedback(state)
    assert "Guardrail de salida: Cita inválida" in result
    assert "Judge: Falta remediación" in result


def test_feedback_changes_between_attempts_so_cache_key_changes():
    # This is the actual bug: two different rejection reasons must produce
    # different rendered prompts (and therefore different cache keys).
    attempt_1 = build_retry_feedback({"guardrail_reason": "reason A"})
    attempt_2 = build_retry_feedback({"guardrail_reason": "reason B"})
    assert attempt_1 != attempt_2
