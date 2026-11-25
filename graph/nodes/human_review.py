import logging

from langgraph.types import interrupt
from graph.state import RegWatchState

logger = logging.getLogger(__name__)


def human_review_checkpoint(state: RegWatchState) -> dict:
    logger.warning(
        "human_review: checkpoint triggered for policy_id=%s judge_attempt=%d",
        state.get("policy_id", "?"), state.get("judge_attempt", 0),
    )
    if state.get("judge_passed"):
        reason = "El judge aprobó el informe. Revise los gaps antes de crear tickets JIRA."
    else:
        reason = state.get("error") or "El judge no aprobó el informe tras los reintentos máximos."
    decision = interrupt({
        "reason": reason,
        "gap_report": state.get("gap_report", {}),
        "judge_scores": state.get("judge_scores", {}),
        "trace_url": state.get("trace_url", ""),
        "iteration": state.get("judge_attempt", 1),
    })
    logger.info("human_review: decision received = %s", decision)
    return {"human_decision": decision}


def route_after_human(state: RegWatchState) -> str:
    if state["human_decision"] != "approve":
        return "analyze_compliance"
    return "error_end" if state.get("error") else "format_report"
