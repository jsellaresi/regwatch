"""Regression test for fix 14 — ADR-0003 documents the real fix.

fix 14 first documented the single-query limitation as a deferred, known
gap. Per follow-up instruction it was then actually implemented (see
tests/test_retrieval_query_decomposition.py for the logic itself) —
this test only checks ADR-0003 was updated to describe what was actually
built, instead of continuing to describe a "deferred" limitation that no
longer accurately reflects the code.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent


def _adr_0003_text() -> str:
    return (REPO_ROOT / "docs" / "ADR-0003-recuperacion-hibrida.md").read_text(encoding="utf-8")


def test_adr_0003_no_longer_describes_this_as_deferred():
    text = _adr_0003_text()
    assert "no implementada" not in text.lower()
    assert "(deferred)" not in text.lower()


def test_adr_0003_documents_the_implemented_decomposition_approach():
    text = _adr_0003_text()
    assert "descomposición de query" in text.lower()
    assert "RecursiveCharacterTextSplitter" in text
    assert "implementada" in text.lower()


def test_adr_0003_mentions_the_real_module_it_describes():
    text = _adr_0003_text()
    assert "graph/nodes/retrieve_regulations.py" in text


def test_retrieve_regulations_source_matches_what_the_adr_describes():
    retrieve_source = (REPO_ROOT / "graph" / "nodes" / "retrieve_regulations.py").read_text(encoding="utf-8")
    assert "RecursiveCharacterTextSplitter" in retrieve_source
    assert "_split_into_queries" in retrieve_source
    assert "_dedup" in retrieve_source
