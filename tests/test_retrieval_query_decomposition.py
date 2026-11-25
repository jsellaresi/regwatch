"""Regression tests for fix 14 (real implementation, not the deferred note).

Before this fix, retrieve_regulations() used a single extracted_text[:2000]
blob as the only retrieval query — a policy mixing GDPR/MiFID/AML topics
across different sections could lose recall before the k=20 candidate set
was even built, since text past char 2000 (or in a later section) never
got a chance to retrieve anything. Documented as a known limitation in
docs/ADR-0003-hybrid-retrieval.md (fix 14's first pass); this is the
real fix, superseding that note.

_split_into_queries and _dedup are pure functions — no live retriever, no
DB, no embeddings — so these tests exercise the actual decomposition/dedup
logic directly. graph.nodes.retrieve_regulations is inside the `graph`
package (LangChain/torch import chain, ~15-85s depending on system load,
same variance observed throughout this session) — accepted since verifying
the real wired functions matters more than avoiding that cost.
"""

from types import SimpleNamespace

from graph.nodes.retrieve_regulations import (
    MAX_QUERY_CHARS, MAX_SECTIONS, MIN_SECTION_CHARS, _dedup, _split_into_queries,
)


def _doc(content: str, regulation: str = "GDPR", **extra_metadata):
    return SimpleNamespace(page_content=content, metadata={"regulation": regulation, **extra_metadata})


# ---------------------------------------------------------------------------
# _split_into_queries
# ---------------------------------------------------------------------------

def test_empty_text_yields_no_queries():
    assert _split_into_queries("") == []
    assert _split_into_queries("   \n  ") == []


def test_short_document_is_a_single_unchanged_query():
    text = "Sección 4.2 — Retención de datos: la empresa conserva los datos indefinidamente."
    queries = _split_into_queries(text)
    assert queries == [text]


def test_document_exactly_at_the_char_limit_is_still_one_query():
    text = "x" * MAX_QUERY_CHARS
    assert _split_into_queries(text) == [text]


def test_long_multi_section_document_produces_multiple_queries():
    sections = [f"Sección {i} — Tema {i}: " + ("contenido relevante " * 60) for i in range(1, 5)]
    long_doc = "\n\n".join(sections)
    assert len(long_doc) > MAX_QUERY_CHARS
    queries = _split_into_queries(long_doc)
    assert len(queries) > 1
    assert all(len(q) <= MAX_QUERY_CHARS for q in queries)


def test_section_count_is_capped_for_very_long_documents():
    sections = [f"Sección {i} — Tema {i}: " + ("x" * 900) for i in range(1, 20)]
    long_doc = "\n\n".join(sections)
    queries = _split_into_queries(long_doc)
    assert len(queries) <= MAX_SECTIONS


def test_trivially_short_sections_are_filtered_out():
    # A long document whose "sections" after splitting are mostly stray
    # short fragments shouldn't turn each fragment into its own query.
    long_doc = "A. \n\n" * 500 + ("Sección real — " + "contenido " * 100)
    queries = _split_into_queries(long_doc)
    assert all(len(q.strip()) >= MIN_SECTION_CHARS for q in queries)


def test_falls_back_to_truncated_whole_text_if_nothing_survives_filtering():
    # Pathological case: a long document made entirely of fragments shorter
    # than MIN_SECTION_CHARS. Must not return an empty list for non-empty input.
    long_doc = "x\n\n" * 2000  # each "section" is 1 char, well under MIN_SECTION_CHARS
    queries = _split_into_queries(long_doc)
    assert len(queries) >= 1


# ---------------------------------------------------------------------------
# _dedup
# ---------------------------------------------------------------------------

def test_dedup_collapses_identical_regulation_and_content():
    a = _doc("Art. 17 text", regulation="GDPR")
    b = _doc("Art. 17 text", regulation="GDPR")  # same content, retrieved by a second query
    result = _dedup([a, b])
    assert len(result) == 1
    assert result[0] is a  # first-seen wins


def test_dedup_keeps_same_content_from_different_regulations_distinct():
    a = _doc("shared boilerplate text", regulation="GDPR")
    b = _doc("shared boilerplate text", regulation="MiFID II")
    result = _dedup([a, b])
    assert len(result) == 2


def test_dedup_preserves_first_seen_order():
    a = _doc("first", regulation="GDPR")
    b = _doc("second", regulation="MiFID II")
    c = _doc("first", regulation="GDPR")  # duplicate of a
    result = _dedup([a, b, c])
    assert result == [a, b]


def test_dedup_of_empty_list_is_empty():
    assert _dedup([]) == []
