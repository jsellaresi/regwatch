"""The current Claude models reject sampling parameters: the API answers 400
"`temperature` is deprecated for this model". It broke the first eval-gate run with
the new model IDs, and the real analyzer would have failed the same way.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SKIPPED_DIRS = {".venv", "node_modules", ".git", "tests", "regwatch.egg-info", "dist"}
REJECTED_PARAMS = {"temperature", "top_p", "top_k"}


def offending_calls(source: str) -> list[tuple[int, list[str]]]:
    """(line, rejected keyword arguments) of every ChatAnthropic(...) call in the source."""
    found = []
    for node in ast.walk(ast.parse(source)):
        if not isinstance(node, ast.Call):
            continue
        name = getattr(node.func, "id", getattr(node.func, "attr", ""))
        rejected = [kw.arg for kw in node.keywords if kw.arg in REJECTED_PARAMS]
        if name == "ChatAnthropic" and rejected:
            found.append((node.lineno, rejected))
    return found


def test_the_scanner_flags_a_sampling_parameter_on_an_anthropic_client():
    assert offending_calls("ChatAnthropic(model='m', temperature=0)") == [(1, ["temperature"])]
    assert offending_calls("x = lc.ChatAnthropic(model='m', top_p=0.9, max_tokens=5)") == [(1, ["top_p"])]


def test_the_scanner_ignores_clean_anthropic_calls_and_other_providers():
    assert offending_calls("ChatAnthropic(model='m', max_tokens=256)") == []
    assert offending_calls("ChatOpenAI(model='gpt-4o', temperature=0)") == []


def test_no_anthropic_client_in_the_repo_sets_a_parameter_the_models_reject():
    offenders = []
    for path in REPO_ROOT.rglob("*.py"):
        relative = path.relative_to(REPO_ROOT)
        if SKIPPED_DIRS & set(relative.parts):
            continue
        for line, params in offending_calls(path.read_text(encoding="utf-8")):
            offenders.append((str(relative), line, params))
    assert not offenders, f"ChatAnthropic called with parameters the models reject: {offenders}"
