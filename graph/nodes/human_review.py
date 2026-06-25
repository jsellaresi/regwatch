from langgraph.types import interrupt
from graph.state import RegWatchState


def human_review_checkpoint(state: RegWatchState) -> dict:
    decision = interrupt({
        "reason": "El judge no aprobó el informe tras los reintentos máximos.",
        "gap_report": state["gap_report"],
        "judge_scores": state.get("judge_scores", {}),
        "trace_url": state.get("trace_url", ""),
    })
    return {"human_decision": decision}


def route_after_human(state: RegWatchState) -> str:
    return "format_report" if state["human_decision"] == "approve" else "analyze_compliance"
