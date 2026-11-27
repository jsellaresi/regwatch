"""The enrichment loop must resend the same conversation prefix on every round.

With the current Claude models the first reply carries a signed `thinking` block that is bound to
the system prompt and the messages it was produced from. The loop used to resend only
[reply, tool result], dropping the system prompt and the document, and the API answered 400
("The block is bound to a different conversation"). It also meant the model never saw the document
after its first round.
"""
import importlib
from types import SimpleNamespace

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage, ToolMessage

enrich = importlib.import_module("graph.nodes.enrich_agent")

DOCUMENT = "Política de retención: los datos se conservan de forma indefinida."


def _run(monkeypatch, messages):
    seen = []
    llm = SimpleNamespace(invoke=lambda msgs: (seen.append(msgs), AIMessage(content="ok"))[1])
    monkeypatch.setattr(enrich, "_get_llm_enrich", lambda: llm)
    state = {"extracted_text": DOCUMENT}
    if messages is not None:
        state["messages"] = messages
    enrich.enrich_agent(state)
    return seen[0]


def test_the_first_round_sends_the_system_prompt_and_the_document(monkeypatch):
    sent = _run(monkeypatch, None)
    assert [type(m) for m in sent] == [SystemMessage, HumanMessage]
    assert DOCUMENT in sent[1].content


def test_a_later_round_keeps_the_system_prompt_and_the_document_before_the_tool_exchange(monkeypatch):
    reply = AIMessage(
        content=[{"type": "thinking", "thinking": "...", "signature": "sig"}, {"type": "tool_use", "id": "t1", "name": "x", "input": {}}],
        tool_calls=[{"id": "t1", "name": "x", "args": {}}],
    )
    result = ToolMessage(content="sin enmiendas", tool_call_id="t1")

    sent = _run(monkeypatch, [reply, result])

    assert [type(m) for m in sent] == [SystemMessage, HumanMessage, AIMessage, ToolMessage]
    assert DOCUMENT in sent[1].content
    assert sent[2] is reply and sent[3] is result  # the signed reply goes back untouched


def test_stale_messages_that_do_not_end_in_a_tool_result_do_not_leak_into_a_fresh_round(monkeypatch):
    stale = [AIMessage(content="respuesta anterior")]
    assert [type(m) for m in _run(monkeypatch, stale)] == [SystemMessage, HumanMessage]
