import logging

from psycopg.types.json import Jsonb
from graph.state import RegWatchState
from db import get_pool

logger = logging.getLogger(__name__)


def gap_key(gap: dict) -> str:
    """Identity key for a gap: the regulation reference. Used both to diff
    against episodic memory here and (in create_tickets.py) to decide which
    gaps are genuinely new since the policy's last analysis. Keyed on the
    article, not the description, because the LLM rewords descriptions between
    runs and a description-based key reported the same gap as resolved and new.
    Trade-off: two distinct gaps on the same article count as one."""
    return gap["regulation_ref"].strip()


def _gap_keys(report: dict) -> set[str]:
    return {gap_key(g) for g in report.get("gaps", [])}


async def diff_with_memory(state: RegWatchState) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "SELECT gap_report FROM policy_episodes WHERE policy_id = %s "
            "ORDER BY created_at DESC LIMIT 1", (state["policy_id"],))
        row = await cur.fetchone()
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


async def store_episodic_memory(state: RegWatchState) -> dict:
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            "INSERT INTO policy_episodes (policy_id, gap_report) VALUES (%s, %s)",
            (state["policy_id"], Jsonb(state["gap_report"])))
    logger.info("episodic_memory: stored for policy_id=%s", state["policy_id"])
    return {}
