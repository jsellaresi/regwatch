"""Regression test for fix 15 — doc-only, no code changed.

Before this fix, ADR-0010 claimed the analyzer uses claude-sonnet-4-6, but
config.py's MODEL_ANALYZER is actually claude-haiku-4-5 (likely a copy-paste
from MODEL_VISION, which really is claude-sonnet-4-6 and sits right next to
it). Fixed the ADR to match the code — not the other way around, since
changing MODEL_ANALYZER would be a real cost/latency decision, not a doc fix.

Reads config.py's source text directly rather than importing it, so this
test doesn't need to pay for the `graph` package's heavy import chain for a
one-line string check (config.py itself is fast to import, but keeping this
test import-free at all keeps it consistent with the other doc-alignment
tests in this suite).
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _adr_0010_text() -> str:
    return (REPO_ROOT / "docs" / "ADR-0010-agent-as-judge.md").read_text(encoding="utf-8")


def _config_text() -> str:
    return (REPO_ROOT / "config.py").read_text(encoding="utf-8")


def test_adr_0010_no_longer_claims_sonnet_for_the_analyzer():
    assert "claude-sonnet-4-6" not in _adr_0010_text()


def test_adr_0010_states_the_real_analyzer_model():
    assert "claude-haiku-4-5" in _adr_0010_text()


def test_adr_0010_matches_config_model_analyzer():
    config_text = _config_text()
    assert 'MODEL_ANALYZER      = "claude-haiku-4-5"' in config_text
    assert "claude-haiku-4-5" in _adr_0010_text()


def test_adr_0010_still_correctly_documents_the_judge_model():
    # Unrelated to this fix — just make sure the correction didn't
    # accidentally touch the (already-correct) judge model claim.
    assert "gpt-4o" in _adr_0010_text()
