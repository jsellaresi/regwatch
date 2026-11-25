import logging

from psycopg.types.json import Jsonb
from graph.state import RegWatchState
from config import CACHE_TTL_SECONDS
from db import get_pool

logger = logging.getLogger(__name__)


async def check_cache(state: RegWatchState) -> dict:
    doc_hash = state["doc_hash"]
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """SELECT final_report FROM analysis_cache
               WHERE doc_hash = %s
                 AND created_at > now() - (%s || ' seconds')::interval""",
            (doc_hash, CACHE_TTL_SECONDS),
        )
        row = await cur.fetchone()
    if row:
        logger.info("check_cache: HIT hash=%s", doc_hash[:12])
        return {"doc_hash": doc_hash, "cache_hit": True, "final_report": row[0]}
    logger.info("check_cache: MISS hash=%s", doc_hash[:12])
    return {"doc_hash": doc_hash, "cache_hit": False}


async def write_cache(state: RegWatchState) -> dict:
    logger.info("write_cache: hash=%s", state["doc_hash"][:12])
    pool = await get_pool()
    async with pool.connection() as conn, conn.cursor() as cur:
        await cur.execute(
            """INSERT INTO analysis_cache (doc_hash, final_report)
               VALUES (%s, %s)
               ON CONFLICT (doc_hash) DO UPDATE
                 SET final_report = EXCLUDED.final_report, created_at = now()""",
            (state["doc_hash"], Jsonb(state["final_report"])),
        )
    return {}


def route_after_cache(state: RegWatchState) -> str:
    return "cache_hit_end" if state["cache_hit"] else "multimodal_extract"
