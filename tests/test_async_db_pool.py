"""Regression tests for fix 16 (async connection pool, not blocking psycopg2).

Before this fix, graph/nodes/cache.py and graph/nodes/memory.py used
`psycopg2.connect(...)` synchronously inside nodes that run in an async
graph — blocking the event loop during every query — and
`with psycopg2.connect(...) as conn:` commits on exit but never closes the
connection, leaking one connection per call (cache.py had 2 call sites,
memory.py had 2 — 4 leaks per full analysis).

Fixed by sharing the same AsyncConnectionPool the LangGraph checkpointer
already uses (graph/builder.py), via a new tiny `db.py` module (kept
separate from builder.py specifically to avoid a circular import: builder.py
already imports graph.nodes, and graph.nodes.cache/memory would otherwise
need to import back from builder.py).

No live Postgres is available in this environment, so these tests verify
the wiring (functions are actually async now, all four share the same pool
getter, no bare psycopg2.connect remains) rather than executing real
queries — the query logic itself is unchanged (same SQL, same parameter
order), only sync-vs-async and connection-sourcing changed.
"""

import inspect
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_db_module_provides_a_lazy_singleton_pool():
    import db

    assert inspect.iscoroutinefunction(db.get_pool)
    assert db._pool is None  # not opened at import time


def test_cache_functions_are_now_async():
    from graph.nodes import cache

    assert inspect.iscoroutinefunction(cache.check_cache)
    assert inspect.iscoroutinefunction(cache.write_cache)
    # route_after_cache is pure routing logic, not a DB call — stays sync.
    assert not inspect.iscoroutinefunction(cache.route_after_cache)


def test_memory_functions_are_now_async():
    from graph.nodes import memory

    assert inspect.iscoroutinefunction(memory.diff_with_memory)
    assert inspect.iscoroutinefunction(memory.store_episodic_memory)


def test_format_report_awaits_diff_with_memory():
    from graph.nodes.format_report import format_report

    assert inspect.iscoroutinefunction(format_report)
    source = inspect.getsource(format_report)
    assert "await diff_with_memory(state)" in source


def test_no_bare_psycopg2_connect_remains_in_cache_or_memory():
    for path in ("graph/nodes/cache.py", "graph/nodes/memory.py"):
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert "psycopg2" not in source, f"{path} still references psycopg2 directly"
        assert "get_pool" in source


def test_cache_and_memory_and_builder_all_share_the_same_pool_getter():
    # The whole point of db.py: one pool, not one per module.
    for path in ("graph/nodes/cache.py", "graph/nodes/memory.py", "graph/builder.py"):
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert "from db import get_pool" in source


def test_writes_use_jsonb_wrapper_not_manual_json_dumps():
    # psycopg3 (unlike psycopg2) needs an explicit Jsonb(...) wrapper to
    # adapt a Python dict for a jsonb column — a bare json.dumps(...) string
    # relies on implicit text->jsonb casting that isn't the psycopg3-idiomatic
    # (or most robust) way to do it.
    for path in ("graph/nodes/cache.py", "graph/nodes/memory.py"):
        source = (REPO_ROOT / path).read_text(encoding="utf-8")
        assert "Jsonb(" in source
        assert "json.dumps" not in source
