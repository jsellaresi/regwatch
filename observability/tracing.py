from langfuse.decorators import observe, langfuse_context
from config import langfuse


def enrich_trace(state: dict, node_name: str, extra: dict = None):
    langfuse_context.update_current_observation(
        metadata={
            "node": node_name,
            "document_name": state.get("document_name"),
            "prompt_version": state.get("prompt_version"),
            "judge_attempt": state.get("judge_attempt"),
            **(extra or {}),
        }
    )


def log_judge_scores(state: dict):
    scores = state.get("judge_scores", {})
    trace_id = langfuse_context.get_current_trace_id()
    if trace_id and scores:
        langfuse.score(trace_id=trace_id, name="legal_accuracy",
                       value=scores.get("legal_accuracy", 0))
        langfuse.score(trace_id=trace_id, name="citation_quality",
                       value=scores.get("citation_quality", 0))
        langfuse.score(trace_id=trace_id, name="actionability",
                       value=scores.get("actionability", 0))
        langfuse.score(trace_id=trace_id, name="overall_score",
                       value=scores.get("overall_score", 0))
