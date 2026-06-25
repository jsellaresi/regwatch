import logging

from graph.state import RegWatchState
from graph.nodes.memory import diff_with_memory

logger = logging.getLogger(__name__)


def format_report(state: RegWatchState) -> dict:
    memory_diff = diff_with_memory(state)["memory_diff"]
    final = {
        "status": "completed",
        "document_name": state["document_name"],
        "policy_id": state["policy_id"],
        "gaps": state["gap_report"].get("gaps", []),
        "judge_scores": state.get("judge_scores", {}),
        "memory_diff": memory_diff,
        "prompt_version": state.get("prompt_version", ""),
        "trace_url": state.get("trace_url", ""),
        "human_reviewed": bool(state.get("human_decision")),
    }
    logger.info(
        "format_report: %d gaps, human_reviewed=%s, prompt_version=%s",
        len(final["gaps"]), final["human_reviewed"], final["prompt_version"],
    )
    return {"final_report": final, "memory_diff": memory_diff}
