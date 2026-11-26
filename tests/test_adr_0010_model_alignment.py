"""ADR-0010 must name the models config.py actually uses.

The ADR once claimed the analyzer ran on the vision model (a copy-paste from the
neighbouring MODEL_VISION line). This reads the model IDs from config.py's source
instead of pinning literal strings, so upgrading a model only needs config.py and the
ADR to change together, not this test.

It reads config.py as text rather than importing it, to keep this doc-alignment test
free of any import chain.
"""
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _adr_0010_text() -> str:
    return (REPO_ROOT / "docs" / "ADR-0010-agent-as-judge.md").read_text(encoding="utf-8")


def _config_model(name: str) -> str:
    source = (REPO_ROOT / "config.py").read_text(encoding="utf-8")
    match = re.search(rf'^{name}\s*=\s*"([^"]+)"', source, re.MULTILINE)
    assert match, f"{name} not found in config.py"
    return match.group(1)


def test_adr_0010_states_the_analyzer_model_that_config_uses():
    assert _config_model("MODEL_ANALYZER") in _adr_0010_text()


def test_adr_0010_does_not_attribute_the_vision_model_to_the_analyzer():
    vision, analyzer = _config_model("MODEL_VISION"), _config_model("MODEL_ANALYZER")
    if vision != analyzer:
        assert vision not in _adr_0010_text()


def test_adr_0010_documents_the_judge_model_that_config_uses():
    assert _config_model("MODEL_JUDGE") in _adr_0010_text()
