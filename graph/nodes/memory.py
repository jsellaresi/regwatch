import json
import logging

import psycopg2
from graph.state import RegWatchState
from config import DATABASE_URL

logger = logging.getLogger(__name__)


def gap_key(gap: dict) -> str:
    """Identity key for a gap, used both to diff against episodic memory
    here and (in create_tickets.py) to decide which gaps are genuinely new
    since the policy's last analysis. Kept as a single shared function so
    the two can't independently drift apart."""
    return f"{gap['regulation_ref']}::{gap['gap_description'][:80]}"


def _gap_keys(report: dict) -> set[str]:
    return {gap_key(g) for g in report.get("gaps", [])}


def diff_with_memory(state: RegWatchState) -> dict:
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT gap_report FROM policy_episodes WHERE policy_id = %s "
            "ORDER BY created_at DESC LIMIT 1", (state["policy_id"],))
        row = cur.fetchone()
    prev = _gap_keys(row[0]) if row else set()
    curr = _gap_keys(state["gap_report"])
    memory_diff = {
        "resolved":   sorted(prev - curr),
        "still_open": sorted(prev & curr),
        "new":        sorted(curr - prev),
    }
    logger.info(
        "memory_diff: policy_id=%s new=%d resolved=%d still_open=%d",
        state["policy_id"], len(memory_diff["new"]),
        len(memory_diff["resolved"]), len(memory_diff["still_open"]),
    )
    return {"memory_diff": memory_diff}


def store_episodic_memory(state: RegWatchState) -> dict:
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO policy_episodes (policy_id, gap_report) VALUES (%s, %s)",
            (state["policy_id"], json.dumps(state["gap_report"])))
    logger.info("episodic_memory: stored for policy_id=%s", state["policy_id"])
    return {}
