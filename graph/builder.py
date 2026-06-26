import logging
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from psycopg_pool import AsyncConnectionPool
from graph.state import RegWatchState
from graph.nodes import (
    check_cache, write_cache, route_after_cache,
    multimodal_extract,
    input_guardrail, output_guardrail,
    route_after_input_guardrail, route_after_output_guardrail,
    retrieve_regulations, rerank,
    enrich_agent, tools_node, route_enrich, collect_tool_results,
    analyze_compliance,
    agent_judge, route_after_judge,
    human_review_checkpoint, route_after_human,
    format_report, create_tickets, store_episodic_memory,
)
from config import DATABASE_URL

logger = logging.getLogger(__name__)

_graph = None


def create_blocked_end(state: RegWatchState) -> dict:
    return {"final_report": {"error": state["guardrail_reason"], "status": "blocked"}}


def cache_hit_end(state: RegWatchState) -> dict:
    return {}


def create_regwatch_graph(checkpointer):
    b = StateGraph(RegWatchState)

    for name, fn in [
        ("check_cache", check_cache), ("cache_hit_end", cache_hit_end),
        ("multimodal_extract", multimodal_extract),
        ("input_guardrail", input_guardrail), ("blocked_end", create_blocked_end),
        ("retrieve_regulations", retrieve_regulations), ("rerank", rerank),
        ("enrich_agent", enrich_agent), ("tools_node", tools_node),
        ("collect_tool_results", collect_tool_results),
        ("analyze_compliance", analyze_compliance), ("output_guardrail", output_guardrail),
        ("agent_judge", agent_judge), ("human_review_checkpoint", human_review_checkpoint),
        ("format_report", format_report), ("write_cache", write_cache),
        ("create_tickets", create_tickets), ("store_episodic_memory", store_episodic_memory),
    ]:
        b.add_node(name, fn)

    b.add_edge(START, "check_cache")
    b.add_conditional_edges("check_cache", route_after_cache,
                            {"cache_hit_end": "cache_hit_end",
                             "multimodal_extract": "multimodal_extract"})
    b.add_edge("cache_hit_end", END)

    b.add_edge("multimodal_extract", "input_guardrail")
    b.add_conditional_edges("input_guardrail", route_after_input_guardrail,
                            ["retrieve_regulations", "enrich_agent", "blocked_end"])
    b.add_edge("blocked_end", END)

    b.add_edge("retrieve_regulations", "rerank")
    b.add_conditional_edges("enrich_agent", route_enrich,
                            {"tools_node": "tools_node", "enrich_done": "collect_tool_results"})
    b.add_edge("tools_node", "enrich_agent")

    b.add_edge(["rerank", "collect_tool_results"], "analyze_compliance")

    b.add_edge("analyze_compliance", "output_guardrail")
    b.add_conditional_edges("output_guardrail", route_after_output_guardrail,
                            {"agent_judge": "agent_judge",
                             "analyze_compliance": "analyze_compliance",
                             "human_review_checkpoint": "human_review_checkpoint"})

    b.add_conditional_edges("agent_judge", route_after_judge,
                            {"format_report": "format_report",
                             "analyze_compliance": "analyze_compliance",
                             "human_review_checkpoint": "human_review_checkpoint"})

    b.add_conditional_edges("human_review_checkpoint", route_after_human,
                            {"format_report": "format_report",
                             "analyze_compliance": "analyze_compliance"})

    b.add_edge("format_report", "write_cache")
    b.add_edge("write_cache", "create_tickets")
    b.add_edge("create_tickets", "store_episodic_memory")
    b.add_edge("store_episodic_memory", END)

    return b.compile(checkpointer=checkpointer)


async def init_graph():
    global _graph
    logger.info("init_graph: opening async connection pool")
    pool = AsyncConnectionPool(
        conninfo=DATABASE_URL,
        max_size=20,
        open=False,
        kwargs={"autocommit": True, "prepare_threshold": 0},
    )
    await pool.open()
    checkpointer = AsyncPostgresSaver(pool)
    await checkpointer.setup()
    _graph = create_regwatch_graph(checkpointer)
    logger.info("init_graph: graph ready")


def get_graph():
    return _graph
