"""Regression tests for fix 12 (JIRA integration correctness).

Before this fix, tools/regulation_tools.py:42 sent `Authorization: Bearer
{token}` — Jira Cloud requires HTTP Basic auth (email:api_token); Bearer is
a Server/Data Center convention and would 401 against Cloud. It also posted
to the v2 issue API with `description` as plain text, while Cloud's v3 API
(the version consistent with Basic auth) requires ADF. The project key
"COMPL" was hardcoded rather than configurable.

This was never exercised (JIRA_ENABLED=false by default, correctly left
alone), so these tests exercise create_jira_ticket directly with
requests.post monkeypatched — no live JIRA instance involved.
"""

import requests

import tools.regulation_tools as regulation_tools
from tools.regulation_tools import _to_adf, create_jira_ticket


class FakeResponse:
    def __init__(self, status_code=201, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text

    def json(self):
        return self._json_data


# ---------------------------------------------------------------------------
# _to_adf
# ---------------------------------------------------------------------------

def test_to_adf_wraps_plain_text_in_a_paragraph():
    doc = _to_adf("Add a retention clause")
    assert doc["type"] == "doc"
    assert doc["version"] == 1
    assert doc["content"] == [
        {"type": "paragraph", "content": [{"type": "text", "text": "Add a retention clause"}]}
    ]


def test_to_adf_makes_one_paragraph_per_non_empty_line():
    doc = _to_adf("Step 1: do X\n\nStep 2: do Y")
    assert len(doc["content"]) == 2
    assert doc["content"][0]["content"][0]["text"] == "Step 1: do X"
    assert doc["content"][1]["content"][0]["text"] == "Step 2: do Y"


def test_to_adf_handles_empty_text_without_crashing():
    doc = _to_adf("")
    assert doc["content"] == [{"type": "paragraph", "content": []}]


# ---------------------------------------------------------------------------
# create_jira_ticket
# ---------------------------------------------------------------------------

def test_uses_basic_auth_not_bearer(monkeypatch):
    monkeypatch.setattr(regulation_tools, "JIRA_EMAIL", "compliance@example.com")
    monkeypatch.setattr(regulation_tools, "JIRA_API_TOKEN", "secret-token")
    captured = {}

    def fake_post(url, json=None, auth=None, timeout=None):
        captured["url"] = url
        captured["auth"] = auth
        return FakeResponse(status_code=201, json_data={"key": "COMPL-1"})

    monkeypatch.setattr(regulation_tools.requests, "post", fake_post)
    create_jira_ticket.invoke({"summary": "Gap", "description": "Fix it", "priority": "High"})

    assert captured["auth"] is not None
    assert isinstance(captured["auth"], requests.auth.HTTPBasicAuth)
    assert captured["auth"].username == "compliance@example.com"
    assert captured["auth"].password == "secret-token"


def test_uses_v3_api_endpoint(monkeypatch):
    captured = {}

    def fake_post(url, json=None, auth=None, timeout=None):
        captured["url"] = url
        return FakeResponse(status_code=201, json_data={"key": "COMPL-1"})

    monkeypatch.setattr(regulation_tools.requests, "post", fake_post)
    create_jira_ticket.invoke({"summary": "Gap", "description": "Fix it", "priority": "High"})

    assert captured["url"].endswith("/rest/api/3/issue")
    assert "/rest/api/2/issue" not in captured["url"]


def test_description_is_sent_as_adf_not_plain_text(monkeypatch):
    captured = {}

    def fake_post(url, json=None, auth=None, timeout=None):
        captured["payload"] = json
        return FakeResponse(status_code=201, json_data={"key": "COMPL-1"})

    monkeypatch.setattr(regulation_tools.requests, "post", fake_post)
    create_jira_ticket.invoke({"summary": "Gap", "description": "Fix it now", "priority": "High"})

    description = captured["payload"]["fields"]["description"]
    assert isinstance(description, dict)
    assert description["type"] == "doc"


def test_project_key_is_configurable_not_hardcoded(monkeypatch):
    monkeypatch.setattr(regulation_tools, "JIRA_PROJECT_KEY", "CUSTOMKEY")
    captured = {}

    def fake_post(url, json=None, auth=None, timeout=None):
        captured["payload"] = json
        return FakeResponse(status_code=201, json_data={"key": "CUSTOMKEY-1"})

    monkeypatch.setattr(regulation_tools.requests, "post", fake_post)
    create_jira_ticket.invoke({"summary": "Gap", "description": "Fix it", "priority": "High"})

    assert captured["payload"]["fields"]["project"]["key"] == "CUSTOMKEY"


def test_network_exception_is_a_clear_error_not_uncaught(monkeypatch):
    def _raise(*a, **k):
        raise requests.ConnectionError("jira unreachable")

    monkeypatch.setattr(regulation_tools.requests, "post", _raise)
    result = create_jira_ticket.invoke({"summary": "Gap", "description": "Fix it", "priority": "High"})
    assert "jira unreachable" in result


def test_non_201_response_reports_the_error_body(monkeypatch):
    monkeypatch.setattr(regulation_tools.requests, "post",
                         lambda *a, **k: FakeResponse(status_code=400, text="Field 'priority' is required"))
    result = create_jira_ticket.invoke({"summary": "Gap", "description": "Fix it", "priority": "High"})
    assert "Field 'priority' is required" in result
