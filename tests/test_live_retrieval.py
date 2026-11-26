"""Exercises the real hybrid retriever (pgvector semantic search + BM25 built from the
database) and the retrieval eval harness against a real Postgres, with fake
embeddings so it needs no API key. Skipped unless REGWATCH_TEST_DATABASE_URL points at
a disposable database (its name must contain "test"). It proves the plumbing, not
retrieval quality: fake embeddings carry no meaning, and the corpus is tiny.
"""
import hashlib
import os

import psycopg
import pytest
from langchain_core.documents import Document

import retriever
from evals.retrieval_eval import evaluate_retrieval
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


def _corpus(topics):
    """One long article per topic, so each article opens its own chunk."""
    return "\n".join(f"Artículo {n}\n" + (f"{topic} " * 70) for n, topic in topics)


@pytest.fixture
def live_corpus(monkeypatch):
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
    monkeypatch.setattr("langchain_openai.OpenAIEmbeddings", lambda **kw: _FakeEmbeddings())
    monkeypatch.setattr(retriever, "DATABASE_URL", TEST_DB_URL)
    monkeypatch.setattr(retriever, "_hybrid_retriever", None)

    _FakeLoader.text = _corpus([(5, "conservacion indefinida supresion plazo"), (6, "licitud consentimiento base")])
    ing.ingest_regulation("x.pdf", "GDPR", "32016R0679", "http://example", "2016-05-04")
    _FakeLoader.text = _corpus([(23, "conflictos intereses divulgacion clientes"), (24, "informacion clientes")])
    ing.ingest_regulation("x.pdf", "MiFID II", "32014L0065", "http://example", "2014-05-15")
    yield
    monkeypatch.setattr(retriever, "_hybrid_retriever", None)


def _keep_top_5(state):
    return {"retrieved_regulations": state["retrieved_regulations"][:5]}


def test_hybrid_retriever_and_eval_harness_run_against_a_real_database(live_corpus):
    cases = [
        {"id": "retention", "document_excerpt": "conservacion indefinida supresion plazo",
         "expected_gaps": [{"regulation_ref": "GDPR Art. 5(1)(e)"}]},
        {"id": "conflicts", "document_excerpt": "conflictos intereses divulgacion clientes",
         "expected_gaps": [{"regulation_ref": "MiFID II Art. 23"}]},
    ]
    report = evaluate_retrieval(cases, rerank_fn=_keep_top_5)
    assert [row["candidates"] > 0 for row in report["rows"]] == [True, True]
    assert report["regulation_hit_rate_before_rerank"] == 1.0
    assert report["article_hit_rate_before_rerank"] == 1.0
