"""The current Claude models return `content` as a list of blocks, not a string. The first real
run of the stack crashed in the input guardrail (`'list' object has no attribute 'strip'`) and
would have stored the repr of the list as the text of every scanned page.
"""
import importlib
from types import SimpleNamespace

import pytest

import document_store
from graph.llm_text import message_text
from graph.nodes import guardrails as g
from scripts.make_fixtures import build_fixtures

mx = importlib.import_module("graph.nodes.multimodal_extract")


def _reply(content):
    return SimpleNamespace(content=content)


@pytest.mark.parametrize(
    "content, expected",
    [
        ("SAFE", "SAFE"),
        ([{"type": "text", "text": "SAFE"}], "SAFE"),
        ([{"type": "text", "text": "BLOCKED: "}, {"type": "text", "text": "inyección"}], "BLOCKED: inyección"),
        ([{"type": "thinking", "thinking": "hmm"}, {"type": "text", "text": "SAFE", "index": 1}], "SAFE"),
        (["SA", "FE"], "SAFE"),
        ([], ""),
    ],
)
def test_message_text_returns_only_the_text_of_either_content_shape(content, expected):
    assert message_text(_reply(content)) == expected


def _guard(monkeypatch, content):
    monkeypatch.setattr(g, "_get_llm_guard", lambda: SimpleNamespace(invoke=lambda prompt: _reply(content)))
    return g.input_guardrail({"extracted_text": "Política de retención de datos.", "document_name": "p.pdf"})


def test_the_input_guardrail_accepts_a_safe_verdict_returned_as_blocks(monkeypatch):
    assert _guard(monkeypatch, [{"type": "text", "text": "SAFE"}])["guardrail_passed"] is True


def test_the_input_guardrail_still_blocks_when_the_blocked_verdict_comes_as_blocks(monkeypatch):
    result = _guard(monkeypatch, [{"type": "thinking", "thinking": "x"}, {"type": "text", "text": "BLOCKED: no es una política"}])
    assert result["guardrail_passed"] is False and result["guardrail_reason"] == "BLOCKED: no es una política"


def test_a_scanned_page_is_stored_as_the_extracted_text_not_as_the_block_list(monkeypatch):
    doc_hash = document_store.put(build_fixtures()["policy_escaneada"])
    transcription = "3. Retención de datos: La empresa conserva todos los registros de clientes de forma indefinida."
    vision = SimpleNamespace(invoke=lambda messages: _reply([{"type": "text", "text": transcription}]))
    monkeypatch.setattr(mx, "_get_llm_vision", lambda: vision)
    monkeypatch.setattr(mx, "get_langfuse", lambda: SimpleNamespace(get_trace_url=lambda: ""))

    text = mx.multimodal_extract({"doc_hash": doc_hash, "document_name": "policy_escaneada.pdf"})["extracted_text"]

    assert transcription in text
    assert "'type'" not in text and "[{" not in text
