import importlib
from pathlib import Path
from types import SimpleNamespace

from langchain_community.document_loaders import PDFPlumberLoader

from scripts.ingest_regulations import split_into_chunks, tag_articles

REPO_ROOT = Path(__file__).resolve().parent.parent
retrieve_mod = importlib.import_module("graph.nodes.retrieve_regulations")


def _chunks(*texts):
    return [SimpleNamespace(page_content=t, metadata={}) for t in texts]


def _tag(*texts):
    chunks = _chunks(*texts)
    tag_articles(chunks)
    return [c.metadata["articles"] for c in chunks]


def test_a_chunk_that_opens_an_article_is_tagged_with_it():
    assert _tag("Artículo 5\nPrincipios relativos al tratamiento") == [[5]]


def test_continuation_chunks_inherit_the_article_that_was_open():
    tags = _tag("Artículo 5\nPrincipios\n1. Los datos serán", "d) exactos;", "e) mantenidos durante no más tiempo")
    assert tags == [[5], [5], [5]]


def test_a_new_header_switches_the_article():
    assert _tag("Artículo 5\nuno", "texto", "Artículo 6\ndos", "texto") == [[5], [5], [6], [6]]


def test_small_adjacent_articles_sharing_a_chunk_are_all_listed_and_the_last_one_carries_on():
    tags = _tag("Artículo 7\ncorto\nArtículo 8\ncorto", "continúa el 8")
    assert tags == [[7, 8], [8]]


def test_a_page_header_before_a_continuation_does_not_break_the_inheritance():
    tags = _tag("Artículo 5\nuno", "L 119/36 ES Diario Oficial de la Unión Europea 4.5.2016\ne) mantenidos")
    assert tags == [[5], [5]]


def test_text_before_the_first_article_has_no_article():
    assert _tag("(39) considerando previo", "Artículo 1\nObjeto") == [[], [1]]


def test_a_lowercase_mid_sentence_cross_reference_is_not_a_header():
    assert _tag("Artículo 9\nconforme al artículo 5 del Reglamento") == [[9]]


def test_gdpr_conservation_limit_chunk_is_traced_back_to_article_5():
    # In the real GDPR PDF Article 5 spans several chunks and the text of 5(1)(e) is not in the
    # one that opens it; a metric that only looked at "Artículo 5" headers counted that as a miss.
    chunks = split_into_chunks(PDFPlumberLoader(str(REPO_ROOT / "data" / "CELEX_32016R0679_ES_TXT.pdf")).load())
    holding = [c for c in chunks if "limitación del plazo de conservación" in c.page_content]
    assert holding, "the phrase of Article 5(1)(e) should appear in the corpus"
    assert any(5 in c.metadata["articles"] for c in holding)
    assert not any(c.page_content.lstrip().startswith("Artículo 5") for c in holding)


def test_retrieved_chunks_carry_their_articles_to_the_state(monkeypatch):
    doc = SimpleNamespace(page_content="e) mantenidos", metadata={"regulation": "GDPR", "articles": [5]})
    monkeypatch.setattr(retrieve_mod, "get_hybrid_retriever", lambda: SimpleNamespace(invoke=lambda query: [doc]))
    out = retrieve_mod.retrieve_regulations({"extracted_text": "Política de retención de datos."})
    assert out["retrieved_regulations"][0]["articles"] == [5]
