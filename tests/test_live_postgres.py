"""Checks that need a real Postgres with pgvector; skipped unless
REGWATCH_TEST_DATABASE_URL points at a disposable database (its name must
contain "test"). They exist because the HNSW fix once passed every string-level
unit test and still crashed on a real database ("column does not have dimensions").
"""
import hashlib
import os
from pathlib import Path

import psycopg
import pytest
from langchain_core.documents import Document

from scripts import ingest_regulations as ing

TEST_DB_URL = os.getenv("REGWATCH_TEST_DATABASE_URL")


class _FakeEmbeddings:
    def _vector(self, text):
        digest = hashlib.sha256(text.encode()).digest()
        return [digest[i % 32] / 255.0 for i in range(1536)]

    def embed_documents(self, texts):
        return [self._vector(t) for t in texts]

    def embed_query(self, text):
        return self._vector(text)


class _FakeLoader:
    text = ""

    def __init__(self, path):
        pass

    def load(self):
        return [Document(page_content=_FakeLoader.text, metadata={})]


def _articles(tag, n):
    return "\n".join(f"Artículo {i} {tag}: " + "texto de prueba sintético " * 40 for i in range(n))


@pytest.fixture
def live_db(monkeypatch):
    if not TEST_DB_URL:
        pytest.skip("REGWATCH_TEST_DATABASE_URL not set")
    assert "test" in TEST_DB_URL.rsplit("/", 1)[-1], "refusing to run destructive tests on a non-test database"
    with psycopg.connect(TEST_DB_URL, autocommit=True) as conn:
        conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
        conn.execute("DROP TABLE IF EXISTS langchain_pg_embedding, langchain_pg_collection CASCADE")
    monkeypatch.setattr(ing, "CONNECTION_STRING", TEST_DB_URL)
    monkeypatch.setattr(ing, "PDFPlumberLoader", _FakeLoader)
    monkeypatch.setattr(ing, "OpenAIEmbeddings", lambda **kw: _FakeEmbeddings())
    monkeypatch.setattr(ing, "invalidate_analysis_cache", lambda reason: None)
    return TEST_DB_URL


def _ingest(celex, name, text):
    _FakeLoader.text = text
    ing.ingest_regulation("x.pdf", name, celex, "http://example", "2020-01-01")


def _counts(url):
    with psycopg.connect(url) as conn, conn.cursor() as cur:
        cur.execute("SELECT cmetadata->>'celex', count(*) FROM langchain_pg_embedding GROUP BY 1")
        return dict(cur.fetchall())


def test_reingest_keeps_one_copy_and_leaves_other_regulations_alone(live_db):
    _ingest("AAA", "GDPR", _articles("A", 6))
    _ingest("BBB", "MiFID II", _articles("B", 4))
    first = _counts(live_db)

    _ingest("AAA", "GDPR", _articles("A", 6))
    assert _counts(live_db) == first

    _ingest("AAA", "GDPR", _articles("A", 2))
    after = _counts(live_db)
    assert after["AAA"] < first["AAA"] and after["BBB"] == first["BBB"]


def test_hnsw_index_is_created_and_used_for_similarity_search(live_db):
    _ingest("AAA", "GDPR", _articles("A", 6))
    with psycopg.connect(live_db) as conn, conn.cursor() as cur:
        cur.execute("SELECT 1 FROM pg_indexes WHERE indexname = 'idx_langchain_pg_embedding_hnsw'")
        assert cur.fetchone() is not None
        query = "[" + ",".join(str(x) for x in _FakeEmbeddings().embed_query("consulta")) + "]"
        cur.execute("SET enable_seqscan = off")  # tiny table: force the planner to pick the index if it can
        cur.execute("EXPLAIN SELECT uuid FROM langchain_pg_embedding ORDER BY embedding <=> %s::vector LIMIT 5", (query,))
        plan = "\n".join(row[0] for row in cur.fetchall())
    assert "idx_langchain_pg_embedding_hnsw" in plan


def test_cache_invalidation_works_on_the_schema_the_migrations_build(live_db, monkeypatch):
    # The eval gate once crashed during ingestion because it only enabled pgvector and
    # never applied the migrations, so `DELETE FROM analysis_cache` hit a missing table.
    import cache_invalidation

    repo = Path(__file__).resolve().parent.parent
    scripts = [repo / "docker" / "init-db.sql", *sorted((repo / "migrations").glob("*.sql"))]
    with psycopg.connect(live_db, autocommit=True) as conn:
        conn.execute("DROP TABLE IF EXISTS analysis_cache, policy_episodes")
        for script in scripts:
            conn.execute(script.read_text(encoding="utf-8"))
        conn.execute("INSERT INTO analysis_cache (doc_hash, final_report) VALUES ('h', '{}')")

    monkeypatch.setattr(cache_invalidation, "DATABASE_URL", live_db)
    cache_invalidation.invalidate_analysis_cache(reason="test")

    with psycopg.connect(live_db) as conn, conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM analysis_cache")
        assert cur.fetchone()[0] == 0


def test_article_tags_are_persisted_on_every_chunk_of_a_long_article(live_db):
    text = "Artículo 5\n" + "principios de tratamiento " * 80 + "\nArtículo 6\n" + "licitud " * 120
    _ingest("AAA", "GDPR", text)
    with psycopg.connect(live_db) as conn, conn.cursor() as cur:
        cur.execute("SELECT cmetadata->>'articles', count(*) FROM langchain_pg_embedding GROUP BY 1")
        tags = dict(cur.fetchall())
    assert tags.get("[5]", 0) >= 2, tags  # the article spans several chunks and all of them are tagged
    assert tags.get("[6]", 0) >= 1, tags
