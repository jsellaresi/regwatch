import importlib
from types import SimpleNamespace

from langchain_core.runnables import RunnableLambda

import config
from graph.schemas import GapReport, JudgeSubScores
from scripts.ingest_regulations import CHUNK_SIZE

rerank_mod = importlib.import_module("graph.nodes.rerank")
analyze_mod = importlib.import_module("graph.nodes.analyze_compliance")
judge_mod = importlib.import_module("graph.nodes.agent_judge")

LABEL_AND_SEPARATOR = len("[MiFID II]\n") + len("\n\n")


def _chunks(count):
    """`count` full-size chunks, each starting with START<n> and ending with END<n>."""
    out = []
    for n in range(1, count + 1):
        start, end = f"START{n:02d} ", f" END{n:02d}"
        body = start + "x" * (CHUNK_SIZE - len(start) - len(end)) + end
        assert len(body) == CHUNK_SIZE
        out.append({"regulation": "MiFID II", "content": body})
    return out


def test_the_context_cap_holds_top_n_full_chunks_with_their_labels():
    assert config.REG_CONTEXT_CHARS >= rerank_mod.TOP_N * (CHUNK_SIZE + LABEL_AND_SEPARATOR)


def test_the_analyzer_prompt_carries_all_top_n_chunks_and_nothing_beyond(monkeypatch):
    seen = []
    analyzer = SimpleNamespace(invoke=lambda msgs: (seen.append(msgs), GapReport(gaps=[]))[1])
    monkeypatch.setattr(analyze_mod, "_get_versioned_prompt", lambda: ("sistema", "1"))
    monkeypatch.setattr(analyze_mod, "_get_analyzer", lambda: analyzer)
    state = {"extracted_text": "política", "retrieved_regulations": _chunks(rerank_mod.TOP_N + 2)}
    analyze_mod.analyze_compliance(state)
    prompt = seen[0][1].content
    assert f"END{rerank_mod.TOP_N:02d}" in prompt  # the last of the TOP_N chunks arrives complete
    assert f"END{rerank_mod.TOP_N + 1:02d}" not in prompt  # the cap's slack never lets a whole extra chunk in


def test_the_judge_sees_the_same_regulation_text_as_the_analyzer(monkeypatch):
    captured = []

    def judge(value):
        captured.append(value.to_string())
        return JudgeSubScores(legal_accuracy=9, citation_quality=9, actionability=9)

    monkeypatch.setattr(judge_mod, "_get_llm_judge", lambda: RunnableLambda(judge))
    monkeypatch.setattr(judge_mod, "log_judge_scores", lambda result: None)
    state = {"gap_report": {"gaps": []}, "extracted_text": "política",
             "retrieved_regulations": _chunks(rerank_mod.TOP_N + 2)}
    judge_mod.agent_judge(state)
    assert f"END{rerank_mod.TOP_N:02d}" in captured[0]
    assert f"END{rerank_mod.TOP_N + 1:02d}" not in captured[0]
