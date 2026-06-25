import hashlib
import json
import psycopg2
from graph.state import RegWatchState
from config import DATABASE_URL, CACHE_TTL_SECONDS


def _hash(document_bytes: bytes) -> str:
    return hashlib.sha256(document_bytes).hexdigest()


def check_cache(state: RegWatchState) -> dict:
    doc_hash = _hash(state["document_bytes"])
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """SELECT final_report FROM analysis_cache
               WHERE doc_hash = %s
                 AND created_at > now() - (%s || ' seconds')::interval""",
            (doc_hash, CACHE_TTL_SECONDS),
        )
        row = cur.fetchone()
    if row:
        return {"doc_hash": doc_hash, "cache_hit": True, "final_report": row[0]}
    return {"doc_hash": doc_hash, "cache_hit": False}


def write_cache(state: RegWatchState) -> dict:
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(
            """INSERT INTO analysis_cache (doc_hash, final_report)
               VALUES (%s, %s)
               ON CONFLICT (doc_hash) DO UPDATE
                 SET final_report = EXCLUDED.final_report, created_at = now()""",
            (state["doc_hash"], json.dumps(state["final_report"])),
        )
    return {}


def route_after_cache(state: RegWatchState) -> str:
    return "cache_hit_end" if state["cache_hit"] else "multimodal_extract"
