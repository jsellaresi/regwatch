"""Regression tests for fix 8 (ADR-0010 judge-score logging).

Before this fix, log_judge_scores existed and worked but nothing called it
(grep confirmed zero call sites) — the ADR and README claimed judge scores
were recorded as LangFuse trace metrics to "detect regressions per prompt
version", but that never happened. Now called from agent_judge() after
scoring.

Also hardens log_judge_scores to be genuinely best-effort: a LangFuse hiccup
(bad credentials, network blip) must not fail an otherwise-successful
compliance judgment — it should log and swallow, not propagate.

observability.tracing only depends on config (lazy, fast to import — see
the earlier import-side-effects fix), so this is tested directly against
the real module with a fake Langfuse client substituted in, rather than
needing any live credentials.
"""

import logging

import pytest

import observability.tracing as tracing


class FakeLangfuse:
    def __init__(self, trace_id="trace-123", raise_on_create_score=False):
        self._trace_id = trace_id
        self._raise = raise_on_create_score
        self.created_scores = []

    def get_current_trace_id(self):
        return self._trace_id

    def create_score(self, trace_id, name, value):
        if self._raise:
            raise RuntimeError("langfuse is down")
        self.created_scores.append((trace_id, name, value))


@pytest.fixture
def fake_langfuse(monkeypatch):
    instance = FakeLangfuse()
    monkeypatch.setattr(tracing, "get_langfuse", lambda: instance)
    return instance


def test_no_judge_scores_is_a_noop_and_never_touches_langfuse(monkeypatch):
    def _fail_if_called():
        raise AssertionError("get_langfuse() should not be called when judge_scores is absent")

    monkeypatch.setattr(tracing, "get_langfuse", _fail_if_called)
    tracing.log_judge_scores({})  # no "judge_scores" key at all
    tracing.log_judge_scores({"judge_scores": {}})  # present but empty


def test_no_active_trace_skips_score_creation(monkeypatch):
    instance = FakeLangfuse(trace_id=None)
    monkeypatch.setattr(tracing, "get_langfuse", lambda: instance)
    tracing.log_judge_scores({"judge_scores": {"overall_score": 8.0}})
    assert instance.created_scores == []


def test_all_four_score_dimensions_are_logged_with_correct_values(fake_langfuse):
    scores = {
        "legal_accuracy": 8,
        "citation_quality": 7,
        "actionability": 9,
        "overall_score": 8.0,
        "critical_issues": ["irrelevant to this test"],
        "approved": True,
    }
    tracing.log_judge_scores({"judge_scores": scores})

    logged = {name: value for _, name, value in fake_langfuse.created_scores}
    assert logged == {
        "legal_accuracy": 8,
        "citation_quality": 7,
        "actionability": 9,
        "overall_score": 8.0,
    }
    assert all(trace_id == "trace-123" for trace_id, _, _ in fake_langfuse.created_scores)


def test_langfuse_failure_is_swallowed_not_propagated(monkeypatch, caplog):
    instance = FakeLangfuse(raise_on_create_score=True)
    monkeypatch.setattr(tracing, "get_langfuse", lambda: instance)
    with caplog.at_level(logging.WARNING):
        tracing.log_judge_scores({"judge_scores": {"overall_score": 5.0}})  # must not raise
    assert any("failed to record scores" in r.message for r in caplog.records)


def test_agent_judge_calls_log_judge_scores():
    # Source-inspected rather than imported: graph.nodes.agent_judge pulls in
    # the whole `graph` package (LangChain/torch), 14-20s just to check one
    # line of wiring.
    from pathlib import Path

    source = (Path(__file__).resolve().parent.parent / "graph" / "nodes" / "agent_judge.py").read_text(encoding="utf-8")
    assert "from observability.tracing import log_judge_scores" in source
    assert "log_judge_scores(result)" in source
