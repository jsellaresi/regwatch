import logging

from langchain_anthropic import ChatAnthropic
from config import MODEL_ENRICH
from langchain_core.messages import SystemMessage, HumanMessage, ToolMessage
from langgraph.prebuilt import ToolNode
from langfuse import observe
from tools.regulation_tools import ENRICH_TOOLS
from graph.state import RegWatchState

logger = logging.getLogger(__name__)

llm_enrich = ChatAnthropic(model=MODEL_ENRICH).bind_tools(ENRICH_TOOLS)
tools_node = ToolNode(ENRICH_TOOLS)

ENRICH_SYSTEM = (
    "Eres un asistente que enriquece un análisis de compliance. Decide si necesitas "
    "consultar enmiendas regulatorias recientes (EUR-Lex) o buscar información adicional. "
    "Si el documento no requiere datos externos, responde sin llamar herramientas."
)


@observe(name="enrich_agent")
def enrich_agent(state: RegWatchState) -> dict:
    existing = state.get("messages") or []
    if existing and isinstance(existing[-1], ToolMessage):
        # Mid-tool-loop: continue with accumulated messages
        msgs = existing
    else:
        # Fresh start (or stale checkpoint): rebuild from scratch
        msgs = [
            SystemMessage(content=ENRICH_SYSTEM),
            HumanMessage(content=f"Documento de política:\n{state['extracted_text'][:3000]}"),
        ]
    response = llm_enrich.invoke(msgs)
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
