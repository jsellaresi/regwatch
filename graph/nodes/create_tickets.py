from graph.state import RegWatchState
from tools.regulation_tools import create_jira_ticket

PRIORITY = {"HIGH": "High", "MEDIUM": "Medium", "LOW": "Low"}


def create_tickets(state: RegWatchState) -> dict:
    ticket_ids = []
    for gap in state["gap_report"].get("gaps", []):
        if gap["risk_level"] in ("HIGH", "MEDIUM"):
            result = create_jira_ticket.invoke({
                "summary": f"[{gap['regulation_ref']}] {gap['gap_description'][:80]}",
                "description": gap["remediation"],
                "priority": PRIORITY[gap["risk_level"]],
            })
            ticket_ids.append(result)
    return {"jira_ticket_ids": ticket_ids}
