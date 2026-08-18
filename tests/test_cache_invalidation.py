"""Regression tests for fix 7 (ADR-0006 cache invalidation).

Before this fix, neither prompt promotion (scripts/promote_prompt.py) nor
regulation re-ingestion (scripts/ingest_regulations.py) touched
analysis_cache at all — the only invalidation mechanism was the 7-day TTL,
which the ADR itself describes as a second safety net, not the primary
mechanism. Scenario from the PDF: promote a prompt v3 that detects a new
gap, and documents already analyzed keep returning the stale report for a
full week.

cache_invalidation.py is intentionally tiny and dependency-light (just
psycopg2 + config.DATABASE_URL) — these tests only check its SQL content
and that the two call sites are wired correctly, not that DELETE actually
runs against a live Postgres.
"""

import inspect
from pathlib import Path

from cache_invalidation import INVALIDATE_ANALYSIS_CACHE_SQL, invalidate_analysis_cache

REPO_ROOT = Path(__file__).resolve().parent.parent


def test_invalidation_sql_clears_the_whole_cache_table():
    # ADR-0006 says "vaciar/expirar el cache" — analysis_cache has no column
    # tracking which prompt version or regulation a cached report used, so a
    # full flush is the only invalidation granularity available.
    assert INVALIDATE_ANALYSIS_CACHE_SQL.strip().upper() == "DELETE FROM ANALYSIS_CACHE"


def test_invalidate_analysis_cache_is_callable_with_a_reason():
    assert callable(invalidate_analysis_cache)
    sig = inspect.signature(invalidate_analysis_cache)
    assert "reason" in sig.parameters


def test_promote_prompt_invalidates_cache_only_when_promoting_to_production():
    # analyze_compliance reads label="production" — promoting to any other
    # label (e.g. "staging") doesn't change live analysis behavior, so there
    # should be nothing to invalidate in that case. Source-inspected rather
    # than executed, since promote_prompt() needs a live Langfuse call.
    source = (REPO_ROOT / "scripts" / "promote_prompt.py").read_text(encoding="utf-8")
    assert "invalidate_analysis_cache" in source
    assert 'to_label == "production"' in source


def test_ingest_regulation_invalidates_cache_after_ingestion():
    source = (REPO_ROOT / "scripts" / "ingest_regulations.py").read_text(encoding="utf-8")
    ingest_start = source.index("def ingest_regulation(")
    ingest_body = source[ingest_start:source.index("\ndef main")]
    assert "invalidate_analysis_cache" in ingest_body
