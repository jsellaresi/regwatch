from typing import TypedDict, Annotated
from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class RegWatchState(TypedDict):
    # ── Input ──────────────────────────────────────────────
    document_name: str
    policy_id: str

    # ── Caching ────────────────────────────────────────────
    # sha256 of the uploaded PDF; the bytes live in document_store, not here.
    doc_hash: str
    cache_hit: bool

    # ── Phase 1: Multimodal extraction ─────────────────────
    extracted_text: str

    # ── Guardrails ─────────────────────────────────────────
    guardrail_passed: bool
    guardrail_reason: str
    output_guardrail_attempt: int

    # ── Retrieval + Tools ──────────────────────────────────
    retrieved_regulations: list[dict]
    tool_results: list[dict]
    messages: Annotated[list[AnyMessage], add_messages]

    # ── Analysis ───────────────────────────────────────────
    prompt_version: str
    gap_report: dict

    # ── Judge ──────────────────────────────────────────────
    judge_scores: dict
    judge_attempt: int
    judge_passed: bool

    # ── Human-in-the-Loop ──────────────────────────────────
    human_decision: str

    # ── Memory (episodic) ──────────────────────────────────
    memory_diff: dict

    # ── Output ─────────────────────────────────────────────
    final_report: dict
    trace_url: str
    jira_ticket_ids: list[str]
    error: str
