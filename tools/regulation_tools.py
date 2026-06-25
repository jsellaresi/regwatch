import requests
from langchain_core.tools import tool
from config import EURLEX_BASE_URL, JIRA_API_TOKEN


@tool
def get_regulation_amendments(regulation_id: str, since_date: str) -> str:
    """
    Consulta EUR-Lex para obtener enmiendas recientes de una regulación.

    Args:
        regulation_id: Identificador EUR-Lex (ej. "32016R0679" para GDPR)
        since_date: Fecha desde la que buscar enmiendas (formato YYYY-MM-DD)
    """
    url = f"{EURLEX_BASE_URL}/document/{regulation_id}/amendments"
    response = requests.get(url, params={"since": since_date}, timeout=10)
    if response.status_code != 200:
        return f"No se encontraron enmiendas para {regulation_id}"
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
    headers = {
        "Authorization": f"Bearer {JIRA_API_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "fields": {
            "project": {"key": "COMPL"},
            "summary": summary,
            "description": description,
            "issuetype": {"name": "Task"},
            "priority": {"name": priority},
        }
    }
    response = requests.post(
        "https://your-org.atlassian.net/rest/api/2/issue",
        json=payload,
        headers=headers,
        timeout=10,
    )
    if response.status_code == 201:
        ticket_id = response.json()["key"]
        return f"Ticket creado: {ticket_id}"
    return f"Error creando ticket: {response.text}"


@tool
def web_search_regulation(query: str) -> str:
    """
    Búsqueda web de fallback para información regulatoria no en el corpus local.

    Args:
        query: Consulta en lenguaje natural sobre regulación
    """
    return f"[Simulado] Resultados de búsqueda para: {query}"


ENRICH_TOOLS = [get_regulation_amendments, web_search_regulation]
