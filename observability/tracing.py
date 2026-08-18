import logging

from config import get_langfuse

logger = logging.getLogger(__name__)


def enrich_trace(state: dict, node_name: str, extra: dict = None):
    # metadata enrichment is handled automatically by the @observe decorator in Langfuse 4.x
    pass


def log_judge_scores(state: dict) -> None:
    """Log judge sub-scores as LangFuse trace metrics (ADR-0010), so score
    regressions are visible per prompt version. Best-effort: a LangFuse
    hiccup (bad creds, network) must not fail an otherwise-successful
    compliance judgment, so failures are logged and swallowed here."""
    scores = state.get("judge_scores") or {}
    if not scores:
        return
    try:
        langfuse = get_langfuse()
        trace_id = langfuse.get_current_trace_id()
        if not trace_id:
            return
        for name in ("legal_accuracy", "citation_quality", "actionability", "overall_score"):
            langfuse.create_score(trace_id=trace_id, name=name, value=scores.get(name, 0))
    except Exception:
        logger.warning("log_judge_scores: failed to record scores to LangFuse", exc_info=True)
