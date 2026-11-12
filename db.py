"""Shared async Postgres connection pool.

One pool, not one-per-caller: graph/builder.py's checkpointer and the ad-hoc
queries in graph/nodes/cache.py and graph/nodes/memory.py all share this
same pool instead of each opening (and, before this fix, leaking — psycopg2's
`with conn:` commits but does not close) their own psycopg2 connections.
"""

import logging

from config import DATABASE_URL

logger = logging.getLogger(__name__)

_pool = None


async def get_pool():
    """Lazily open the pool on first real use — must not open a DB
    connection at import time (see the earlier import-side-effects fix)."""
    global _pool
    if _pool is None:
        from psycopg_pool import AsyncConnectionPool

        pool = AsyncConnectionPool(
            conninfo=DATABASE_URL,
            max_size=20,
            open=False,
            kwargs={"autocommit": True, "prepare_threshold": 0},
        )
        await pool.open()
        _pool = pool
        logger.info("db.get_pool: async connection pool opened")
    return _pool
