from config import langfuse


def enrich_trace(state: dict, node_name: str, extra: dict = None):
    # metadata enrichment is handled automatically by the @observe decorator in Langfuse 4.x
    pass


def log_judge_scores(state: dict):
    scores = state.get("judge_scores", {})
    trace_id = langfuse.get_current_trace_id()
    if trace_id and scores:
        for name in ("legal_accuracy", "citation_quality", "actionability", "overall_score"):
            langfuse.create_score(trace_id=trace_id, name=name,
                                  value=scores.get(name, 0))
