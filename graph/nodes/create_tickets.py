import logging

from langfuse import observe
from graph.state import RegWatchState
from graph.nodes.memory import gap_key
from tools.regulation_tools import create_jira_ticket
from config import JIRA_ENABLED

logger = logging.getLogger(__name__)

PRIORITY = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}


def select_eligible_gaps(gaps: list[dict], memory_diff: dict) -> list[dict]:
    """HIGH/MEDIUM gaps that are genuinely new since this policy's last
    analysis (memory_diff["new"], computed in format_report.py via
    diff_with_memory). Without this, re-analyzing the same policy reopens a
    ticket for every gap that's merely still open, not actually new. On a
    policy's first-ever analysis there's no prior episode, so memory_diff["new"]
    is every current gap — nothing is filtered out."""
    new_keys = set(memory_diff.get("new", []))
    return [g for g in gaps if g["risk_level"] in ("HIGH", "MEDIUM") and gap_key(g) in new_keys]


@observe(name="create_tickets")
def create_tickets(state: RegWatchState) -> dict:
    if not JIRA_ENABLED:
        logger.info("create_tickets: JIRA_ENABLED=false, skipping")
        return {"jira_ticket_ids": []}
    ticket_ids = []
    gaps = state["gap_report"].get("gaps", [])
    eligible = select_eligible_gaps(gaps, state.get("memory_diff", {}))
    logger.info("create_tickets: %d eligible gaps (HIGH/MEDIUM, new since last analysis) out of %d total",
                len(eligible), len(gaps))
    for gap in eligible:
        result = create_jira_ticket.invoke({
            "summary": f"[{gap['regulation_ref']}] {gap['gap_description'][:80]}",
            "description": gap["remediation"],
            "priority": PRIORITY[gap["risk_level"]],
        })
        if result.startswith("Error"):
            logger.error("create_tickets: JIRA error for [%s]", gap["regulation_ref"])
        else:
            logger.info("create_tickets: %s for [%s]", result, gap["regulation_ref"])
        ticket_ids.append(result)
    return {"jira_ticket_ids": ticket_ids}
