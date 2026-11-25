import pytest

from scripts import ingest_regulations as ing


def test_delete_sql_is_scoped_to_one_regulation_and_keeps_new_chunks():
    sql = ing.DELETE_STALE_CHUNKS_SQL
    assert "cmetadata->>'celex' = :celex" in sql
    assert "custom_id <> ALL(:new_ids)" in sql
    assert "name = 'regulations'" in sql


class _FakeChunk:
    def __init__(self):
        self.metadata = {}


@pytest.fixture
def calls(monkeypatch):
    calls = []

    class FakeLoader:
        def __init__(self, path): pass
        def load(self): return ["raw"]

    class FakeSplitter:
        def __init__(self, **kw): pass
        def split_documents(self, docs): return [_FakeChunk(), _FakeChunk()]

    class FakeStore:
        def __init__(self, **kw):
            calls.append(("store_kwargs", sorted(kw)))
        def add_documents(self, chunks):
            calls.append(("add", len(chunks)))
            return ["id1", "id2"]

    monkeypatch.setattr(ing, "PDFPlumberLoader", FakeLoader)
    monkeypatch.setattr(ing, "RecursiveCharacterTextSplitter", FakeSplitter)
    monkeypatch.setattr(ing, "OpenAIEmbeddings", lambda **kw: object())
    monkeypatch.setattr(ing, "PGVector", FakeStore)
    monkeypatch.setattr(ing, "_delete_stale_chunks",
                        lambda cs, celex, ids: calls.append(("delete", celex, ids)) or 3)
    monkeypatch.setattr(ing, "_ensure_hnsw_index", lambda cs: calls.append(("hnsw",)))
    monkeypatch.setattr(ing, "invalidate_analysis_cache", lambda reason: calls.append(("invalidate",)))
    return calls


def test_reingest_inserts_first_then_deletes_only_older_chunks_of_that_celex(calls):
    ing.ingest_regulation("x.pdf", "GDPR", "32016R0679", "url", "2016-05-04")
    steps = [c[0] for c in calls]
    assert steps == ["store_kwargs", "add", "delete", "hnsw", "invalidate"]
    assert ("delete", "32016R0679", ["id1", "id2"]) in calls


def test_store_is_not_built_with_pre_delete_collection(calls):
    ing.ingest_regulation("x.pdf", "GDPR", "32016R0679", "url", "2016-05-04")
    kwargs = next(c[1] for c in calls if c[0] == "store_kwargs")
    assert "pre_delete_collection" not in kwargs


def test_delete_is_skipped_when_nothing_was_inserted():
    assert ing._delete_stale_chunks("postgresql://unused", "32016R0679", []) == 0
