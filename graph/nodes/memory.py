import json
import psycopg2
from graph.state import RegWatchState
from config import DATABASE_URL


def _gap_keys(report: dict) -> set[str]:
    return {f"{g['regulation_ref']}::{g['gap_description'][:80]}" for g in report.get("gaps", [])}


def diff_with_memory(state: RegWatchState) -> dict:
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "SELECT gap_report FROM policy_episodes WHERE policy_id = %s "
            "ORDER BY created_at DESC LIMIT 1", (state["policy_id"],))
        row = cur.fetchone()
    prev = _gap_keys(row[0]) if row else set()
    curr = _gap_keys(state["gap_report"])
    return {"memory_diff": {
        "resolved":   sorted(prev - curr),
        "still_open": sorted(prev & curr),
        "new":        sorted(curr - prev),
    }}


def store_episodic_memory(state: RegWatchState) -> dict:
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            "INSERT INTO policy_episodes (policy_id, gap_report) VALUES (%s, %s)",
            (state["policy_id"], json.dumps(state["gap_report"])))
    return {}
