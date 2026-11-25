import importlib
import tomllib
import types
from pathlib import Path

from langgraph.checkpoint.memory import MemorySaver

from graph.builder import create_regwatch_graph
from graph.nodes.memory import _gap_keys, gap_key

REPO_ROOT = Path(__file__).resolve().parent.parent
ct = importlib.import_module("graph.nodes.create_tickets")


def _gap(ref, description, risk="HIGH"):
    return {"regulation_ref": ref, "gap_description": description, "risk_level": risk, "remediation": "x"}


def test_gap_key_survives_the_llm_rewording_the_description():
    before = _gap("GDPR Art. 5(1)(e)", "Los datos se conservan de forma indefinida.")
    after = _gap("GDPR Art. 5(1)(e)", "No hay plazo máximo de conservación definido para los datos.")
    assert gap_key(before) == gap_key(after)


def test_gap_key_ignores_surrounding_whitespace_but_distinguishes_articles():
    assert gap_key(_gap(" GDPR Art. 17 ", "a")) == gap_key(_gap("GDPR Art. 17", "b"))
    assert gap_key(_gap("GDPR Art. 17", "a")) != gap_key(_gap("GDPR Art. 5(1)(e)", "a"))


def test_reworded_gap_is_still_open_not_resolved_and_new():
    prev = _gap_keys({"gaps": [_gap("MiFID II Art. 23", "No se comunican los conflictos.")]})
    curr = _gap_keys({"gaps": [_gap("MiFID II Art. 23", "Los conflictos no se divulgan a clientes.")]})
    assert prev - curr == set() and curr - prev == set()


def test_reworded_open_gap_does_not_open_a_duplicate_ticket():
    reworded = _gap("MiFID II Art. 23", "Los conflictos no se divulgan a clientes.")
    memory_diff = {"new": [], "still_open": [gap_key(reworded)], "resolved": []}
    assert ct.select_eligible_gaps([reworded], memory_diff) == []


def test_extract_ticket_key():
    assert ct.extract_ticket_key("Ticket creado: COMPL-12") == "COMPL-12"
    assert ct.extract_ticket_key("Error creando ticket: 401 Unauthorized") is None
    assert ct.extract_ticket_key("") is None


def test_create_tickets_stores_only_real_keys_not_error_messages(monkeypatch):
    results = iter(["Ticket creado: COMPL-1", "Error creando ticket: boom"])
    monkeypatch.setattr(ct, "JIRA_ENABLED", True)
    monkeypatch.setattr(ct, "create_jira_ticket", types.SimpleNamespace(invoke=lambda payload: next(results)))
    gaps = [_gap("GDPR Art. 17", "a"), _gap("MiFID II Art. 23", "b")]
    state = {"gap_report": {"gaps": gaps}, "memory_diff": {"new": [gap_key(g) for g in gaps]}}
    assert ct.create_tickets(state) == {"jira_ticket_ids": ["COMPL-1"]}


def test_graph_has_no_unreachable_judge_to_format_report_edge():
    graph = create_regwatch_graph(MemorySaver()).get_graph()
    assert not any(e.source == "agent_judge" and e.target == "format_report" for e in graph.edges)
    assert any(e.source == "agent_judge" and e.target == "human_review_checkpoint" for e in graph.edges)


def test_langchain_classic_is_declared_since_retriever_imports_it():
    deps = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"]["dependencies"]
    assert any(d.split("[")[0].strip() == "langchain-classic" for d in deps)
