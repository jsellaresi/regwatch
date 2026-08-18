"""Shared cache-invalidation helper (ADR-0006).

The 7-day TTL on analysis_cache is a second safety net, not the primary
invalidation mechanism — ADR-0006 explicitly calls invalidation "clave para
corrección en compliance": a cached report can be based on a prompt version
or regulatory text that no longer applies once a prompt is promoted to
production or a regulation is re-ingested. Kept as its own tiny,
dependency-light module (just psycopg2 + config.DATABASE_URL) rather than
inside graph/nodes/cache.py, so that scripts/promote_prompt.py — a small
Langfuse-only CI step — doesn't have to pull in the whole `graph` package
(and its LangChain/torch dependency tree) just to invalidate a cache table.
"""

import logging

import psycopg2
from config import DATABASE_URL

logger = logging.getLogger(__name__)

INVALIDATE_ANALYSIS_CACHE_SQL = "DELETE FROM analysis_cache"


def invalidate_analysis_cache(reason: str) -> None:
    """Clear analysis_cache. `reason` is for the log line only, to make it
    obvious in logs *why* every subsequent analysis is a fresh cache miss."""
    with psycopg2.connect(DATABASE_URL) as conn, conn.cursor() as cur:
        cur.execute(INVALIDATE_ANALYSIS_CACHE_SQL)
    logger.info("analysis_cache invalidated (%s)", reason)
