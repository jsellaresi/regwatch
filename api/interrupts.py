"""Pure helper for reading a pending LangGraph interrupt out of a state
snapshot. Deliberately dependency-free (no FastAPI, no LangGraph import even)
so it can be unit tested in milliseconds — `api/main.py` pulls in a slow
import chain (langchain_openai, PDFPlumberLoader via scripts.ingest_regulations)
that a test of this logic shouldn't have to pay for.
"""


def extract_interrupt_payload(state) -> dict | None:
    """Return the payload of the first pending interrupt in a LangGraph state
    snapshot (as returned by `graph.aget_state(config)`), or None if nothing
    is interrupted.

    `state` only needs a `.tasks` attribute: an iterable of objects each
    exposing `.interrupts` (an iterable of interrupt objects, each optionally
    exposing `.value`) — matching LangGraph's `StateSnapshot`/`PregelTask`.
    """
    interrupts = [i for task in (state.tasks or []) for i in getattr(task, "interrupts", [])]
    if not interrupts:
        return None
    first = interrupts[0]
    return first.value if hasattr(first, "value") else {}
