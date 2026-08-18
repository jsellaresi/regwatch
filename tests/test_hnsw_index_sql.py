"""Regression test for fix 5 (HNSW index).

Before this fix, ADR-0004 decided on an HNSW index but docker/init-db.sql
only had `CREATE EXTENSION IF NOT EXISTS vector;` — every semantic search
was a full scan. This locks in that the DDL actually matches the ADR's
tuning parameters (m=16, ef_construction=64, cosine ops), since a silent
typo here (e.g. m=6 instead of m=16) wouldn't show up as a Python error —
Postgres would just build a differently-tuned index without complaint.

Doesn't require a live Postgres: this only checks the SQL string content,
not that it executes correctly against a real database.
"""

from scripts.ingest_regulations import HNSW_INDEX_SQL


def test_hnsw_index_sql_targets_the_pgvector_embedding_table():
    assert "langchain_pg_embedding" in HNSW_INDEX_SQL


def test_hnsw_index_sql_uses_hnsw_with_cosine_ops():
    assert "USING hnsw" in HNSW_INDEX_SQL
    assert "vector_cosine_ops" in HNSW_INDEX_SQL


def test_hnsw_index_sql_matches_adr_0004_tuning_parameters():
    assert "m = 16" in HNSW_INDEX_SQL
    assert "ef_construction = 64" in HNSW_INDEX_SQL


def test_hnsw_index_sql_is_idempotent_and_named():
    # IF NOT EXISTS requires an explicit index name in Postgres — this also
    # guards against someone "simplifying" it back to the ADR's unnamed
    # `CREATE INDEX ON ...` shorthand, which would break IF NOT EXISTS.
    assert "IF NOT EXISTS" in HNSW_INDEX_SQL
    assert "CREATE INDEX IF NOT EXISTS idx_" in HNSW_INDEX_SQL
