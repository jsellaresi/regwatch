import logging

from langchain_anthropic import ChatAnthropic
from config import MODEL_ENRICH
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langfuse import observe
from tools.regulation_tools import ENRICH_TOOLS
from graph.state import RegWatchState

logger = logging.getLogger(__name__)

# ToolNode itself has no API-key dependency, safe at import time.
tools_node = ToolNode(ENRICH_TOOLS)

_llm_enrich = None


def _get_llm_enrich():
    global _llm_enrich
    if _llm_enrich is None:
        _llm_enrich = ChatAnthropic(model=MODEL_ENRICH).bind_tools(ENRICH_TOOLS)
    return _llm_enrich

ENRICH_SYSTEM = (
    "Eres un asistente que enriquece un análisis de compliance. Decide si necesitas "
    "consultar enmiendas regulatorias recientes (EUR-Lex) o buscar información adicional. "
    "Si el documento no requiere datos externos, responde sin llamar herramientas."
)


@observe(name="enrich_agent")
def enrich_agent(state: RegWatchState) -> dict:
    opening = [
        SystemMessage(content=ENRICH_SYSTEM),
        HumanMessage(content=f"Documento de política:\n{state['extracted_text'][:3000]}"),
    ]
    existing = state.get("messages") or []
    # The opening messages are not kept in the state, so every call rebuilds them. In a later round
    # of the tool loop they must come before the accumulated messages: the model has to see the
    # document, and its reasoning blocks are bound to the conversation they were produced in.
    in_tool_loop = bool(existing) and isinstance(existing[-1], ToolMessage)
    msgs = opening + list(existing) if in_tool_loop else opening
    response = _get_llm_enrich().invoke(msgs)
    if getattr(response, "tool_calls", None):
        logger.info("enrich_agent: %d tool call(s) requested", len(response.tool_calls))
    else:
        logger.info("enrich_agent: no tool calls, enrichment complete")
    return {"messages": [response]}


def route_enrich(state: RegWatchState) -> str:
    last = state["messages"][-1]
    return "tools_node" if getattr(last, "tool_calls", None) else "enrich_done"


def collect_tool_results(state: RegWatchState) -> dict:
    from langchain_core.messages import ToolMessage
    results = [m.content for m in state["messages"] if isinstance(m, ToolMessage)]
    logger.info("collect_tool_results: %d tool results", len(results))
    return {"tool_results": [{"result": r} for r in results]}
