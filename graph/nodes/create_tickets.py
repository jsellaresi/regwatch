import logging

from langfuse import observe
from graph.state import RegWatchState
from tools.regulation_tools import create_jira_ticket
from config import JIRA_ENABLED

logger = logging.getLogger(__name__)

PRIORITY = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}


@observe(name="create_tickets")
def create_tickets(state: RegWatchState) -> dict:
    if not JIRA_ENABLED:
        logger.info("create_tickets: JIRA_ENABLED=false, skipping")
        return {"jira_ticket_ids": []}
    ticket_ids = []
    gaps = state["gap_report"].get("gaps", [])
    eligible = [g for g in gaps if g["risk_level"] in ("HIGH", "MEDIUM")]
    logger.info("create_tickets: %d eligible gaps (HIGH/MEDIUM) out of %d total", len(eligible), len(gaps))
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
