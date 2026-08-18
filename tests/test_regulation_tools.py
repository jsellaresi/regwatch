"""Regression tests for fix 10 (enrich_agent tools).

Before this fix:
- get_regulation_amendments always got a 404 from a REST path that doesn't
  exist on EUR-Lex (which exposes SPARQL/Cellar, not this shape), and
  translated every non-200 response into "No se encontraron enmiendas" — a
  false negative indistinguishable from a real empty result. The analyzer
  had no way to tell "I checked, there are none" from "the check itself
  failed". Fixed to return a distinct [ERROR]-prefixed message instead —
  the real Cellar/SPARQL integration is a larger follow-up, not part of
  this fix.
- web_search_regulation was an explicit stub returning fake "[Simulado]"
  results regardless of query. Replaced with a real Tavily-backed
  implementation over `requests` (already a dependency — no new package
  needed), gated on TAVILY_API_KEY like the existing COHERE_API_KEY/
  JIRA_ENABLED optional-integration pattern.

Uses `.invoke({...})` (the real LangGraph/ToolNode calling convention) with
requests.get/requests.post monkeypatched — no real network calls.
"""

import requests

import tools.regulation_tools as regulation_tools
from tools.regulation_tools import get_regulation_amendments, web_search_regulation


class FakeResponse:
    def __init__(self, status_code=200, json_data=None):
        self.status_code = status_code
        self._json_data = json_data or {}

    def json(self):
        return self._json_data


# ---------------------------------------------------------------------------
# get_regulation_amendments
# ---------------------------------------------------------------------------

def test_non_200_response_is_a_distinct_error_not_a_false_negative(monkeypatch):
    monkeypatch.setattr(regulation_tools.requests, "get", lambda *a, **k: FakeResponse(status_code=404))
    result = get_regulation_amendments.invoke({"regulation_id": "32016R0679", "since_date": "2024-01-01"})
    assert result.startswith("[ERROR]")
    assert "404" in result
    assert "No se encontraron enmiendas" not in result


def test_network_exception_is_a_distinct_error_not_swallowed(monkeypatch):
    def _raise(*a, **k):
        raise requests.ConnectionError("EUR-Lex unreachable")

    monkeypatch.setattr(regulation_tools.requests, "get", _raise)
    result = get_regulation_amendments.invoke({"regulation_id": "32016R0679", "since_date": "2024-01-01"})
    assert result.startswith("[ERROR]")
    assert "EUR-Lex unreachable" in result


def test_successful_response_with_amendments_is_formatted(monkeypatch):
    data = {"amendments": [{"date": "2024-03-01", "summary": "Art. 5 clarified"}]}
    monkeypatch.setattr(regulation_tools.requests, "get",
                         lambda *a, **k: FakeResponse(status_code=200, json_data=data))
    result = get_regulation_amendments.invoke({"regulation_id": "32016R0679", "since_date": "2024-01-01"})
    assert "2024-03-01" in result
    assert "Art. 5 clarified" in result


def test_successful_response_with_no_amendments_is_a_legitimate_empty_result(monkeypatch):
    monkeypatch.setattr(regulation_tools.requests, "get",
                         lambda *a, **k: FakeResponse(status_code=200, json_data={"amendments": []}))
    result = get_regulation_amendments.invoke({"regulation_id": "32016R0679", "since_date": "2024-01-01"})
    assert not result.startswith("[ERROR]")
    assert "Sin enmiendas recientes" in result


# ---------------------------------------------------------------------------
# web_search_regulation
# ---------------------------------------------------------------------------

def test_no_api_key_returns_explicit_unavailable_message_not_fake_results(monkeypatch):
    monkeypatch.setattr(regulation_tools, "TAVILY_API_KEY", "")
    result = web_search_regulation.invoke({"query": "GDPR retention period"})
    assert "[Simulado]" not in result
    assert "TAVILY_API_KEY" in result


def test_successful_search_is_formatted_from_real_results(monkeypatch):
    monkeypatch.setattr(regulation_tools, "TAVILY_API_KEY", "fake-key")
    results = {"results": [{"title": "GDPR Art. 5", "content": "Storage limitation principle...", "url": "https://example.com"}]}
    monkeypatch.setattr(regulation_tools.requests, "post", lambda *a, **k: FakeResponse(status_code=200, json_data=results))
    result = web_search_regulation.invoke({"query": "GDPR retention period"})
    assert "GDPR Art. 5" in result
    assert "https://example.com" in result


def test_search_non_200_is_a_distinct_error(monkeypatch):
    monkeypatch.setattr(regulation_tools, "TAVILY_API_KEY", "fake-key")
    monkeypatch.setattr(regulation_tools.requests, "post", lambda *a, **k: FakeResponse(status_code=401))
    result = web_search_regulation.invoke({"query": "GDPR retention period"})
    assert result.startswith("[ERROR]")


def test_search_network_exception_is_a_distinct_error(monkeypatch):
    monkeypatch.setattr(regulation_tools, "TAVILY_API_KEY", "fake-key")

    def _raise(*a, **k):
        raise requests.Timeout("timed out")

    monkeypatch.setattr(regulation_tools.requests, "post", _raise)
    result = web_search_regulation.invoke({"query": "GDPR retention period"})
    assert result.startswith("[ERROR]")


def test_search_no_results_is_a_legitimate_empty_result(monkeypatch):
    monkeypatch.setattr(regulation_tools, "TAVILY_API_KEY", "fake-key")
    monkeypatch.setattr(regulation_tools.requests, "post",
                         lambda *a, **k: FakeResponse(status_code=200, json_data={"results": []}))
    result = web_search_regulation.invoke({"query": "GDPR retention period"})
    assert not result.startswith("[ERROR]")
    assert "Sin resultados" in result
