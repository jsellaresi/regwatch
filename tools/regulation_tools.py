import logging

import requests
from requests.auth import HTTPBasicAuth
from langchain_core.tools import tool
from config import (
    EURLEX_BASE_URL, JIRA_API_TOKEN, JIRA_BASE_URL, JIRA_EMAIL, JIRA_PROJECT_KEY, TAVILY_API_KEY,
)

logger = logging.getLogger(__name__)


def _to_adf(text: str) -> dict:
    """Minimal Atlassian Document Format conversion: one paragraph per
    non-empty line. Jira Cloud's v3 issue API requires `description` in ADF,
    not plain text — v2 accepted plain text but is the wrong API version for
    Cloud's Basic-auth model this tool now uses."""
    paragraphs = [
        {"type": "paragraph", "content": [{"type": "text", "text": line}]}
        for line in text.splitlines() if line.strip()
    ]
    return {"type": "doc", "version": 1, "content": paragraphs or [{"type": "paragraph", "content": []}]}


@tool
def get_regulation_amendments(regulation_id: str, since_date: str) -> str:
    """
    Consulta EUR-Lex para obtener enmiendas recientes de una regulación.

    Args:
        regulation_id: Identificador EUR-Lex (ej. "32016R0679" para GDPR)
        since_date: Fecha desde la que buscar enmiendas (formato YYYY-MM-DD)
    """
    url = f"{EURLEX_BASE_URL}/document/{regulation_id}/amendments"
    try:
        response = requests.get(url, params={"since": since_date}, timeout=10)
    except requests.RequestException as exc:
        logger.error("EUR-Lex: amendments request failed for %s: %s", regulation_id, exc)
        return (
            f"[ERROR] No se pudo consultar enmiendas para {regulation_id}: {exc}. "
            "La consulta falló, no dio un resultado negativo — no asumas que no hay enmiendas."
        )
    logger.info("EUR-Lex: GET amendments for %s since %s → status %d", regulation_id, since_date, response.status_code)
    if response.status_code != 200:
        # This endpoint (rest/document/{id}/amendments) doesn't exist on EUR-Lex
        # today (EUR-Lex exposes SPARQL/Cellar, not this REST shape) — it always
        # 404s. Surface that as a distinct failure rather than a false "no
        # amendments found", so the analyzer doesn't treat a broken lookup as a
        # verified negative. Replacing this with the real SPARQL/Cellar query is
        # a larger follow-up, not part of this fix.
        logger.error("EUR-Lex: amendments lookup failed for %s: status %d", regulation_id, response.status_code)
        return (
            f"[ERROR] No se pudo consultar enmiendas para {regulation_id}: "
            f"la API de EUR-Lex devolvió status {response.status_code}. "
            "La consulta falló, no dio un resultado negativo — no asumas que no hay enmiendas."
        )
    data = response.json()
    amendments = data.get("amendments", [])
    if not amendments:
        return f"Sin enmiendas recientes para {regulation_id} desde {since_date}"
    return "\n".join([f"- {a['date']}: {a['summary']}" for a in amendments[:5]])


@tool
def create_jira_ticket(summary: str, description: str, priority: str) -> str:
    """
    Crea un ticket de remediación en JIRA.

    Args:
        summary: Título corto del gap (máx 100 caracteres)
        description: Descripción detallada con pasos de remediación
        priority: "High", "Medium" o "Low"
    """
    payload = {
        "fields": {
            "project": {"key": JIRA_PROJECT_KEY},
            "summary": summary,
            "description": _to_adf(description),
            "issuetype": {"name": "Task"},
            "priority": {"name": priority},
        }
    }
    try:
        response = requests.post(
            f"{JIRA_BASE_URL}/rest/api/3/issue",
            json=payload,
            # Jira Cloud requires HTTP Basic auth (email:api_token), not
            # Bearer — Bearer is a Jira Server/Data Center convention and
            # would 401 against Cloud.
            auth=HTTPBasicAuth(JIRA_EMAIL, JIRA_API_TOKEN),
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.error("JIRA: ticket creation request failed: %s", exc)
        return f"Error creando ticket: {exc}"
    logger.info("JIRA: create ticket priority=%s → status %d", priority, response.status_code)
    if response.status_code == 201:
        ticket_id = response.json()["key"]
        return f"Ticket creado: {ticket_id}"
    logger.error("JIRA: ticket creation failed with status %d", response.status_code)
    return f"Error creando ticket: {response.text}"


@tool
def web_search_regulation(query: str) -> str:
    """
    Búsqueda web de fallback para información regulatoria no en el corpus local.

    Args:
        query: Consulta en lenguaje natural sobre regulación
    """
    if not TAVILY_API_KEY:
        return "Búsqueda web no disponible: falta configurar TAVILY_API_KEY."
    try:
        response = requests.post(
            "https://api.tavily.com/search",
            json={"api_key": TAVILY_API_KEY, "query": query, "max_results": 3},
            timeout=10,
        )
    except requests.RequestException as exc:
        logger.error("Tavily: search request failed: %s", exc)
        return f"[ERROR] Búsqueda web falló para '{query}': {exc}"
    if response.status_code != 200:
        logger.error("Tavily: search failed for '%s': status %d", query, response.status_code)
        return f"[ERROR] Búsqueda web falló para '{query}': status {response.status_code}"
    results = response.json().get("results", [])
    if not results:
        return f"Sin resultados de búsqueda web para: {query}"
    return "\n".join(
        f"- {r.get('title', 'Sin título')}: {r.get('content', '')[:200]} ({r.get('url', '')})"
        for r in results[:3]
    )


ENRICH_TOOLS = [get_regulation_amendments, web_search_regulation]
