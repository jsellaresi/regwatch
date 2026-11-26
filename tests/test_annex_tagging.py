from pathlib import Path
from types import SimpleNamespace

from langchain_community.document_loaders import PDFPlumberLoader

from scripts.ingest_regulations import ANNEX_HEADER_RE, split_into_chunks, tag_articles

REPO_ROOT = Path(__file__).resolve().parent.parent


def _tag(*texts):
    chunks = [SimpleNamespace(page_content=t, metadata={}) for t in texts]
    tag_articles(chunks)
    return [c.metadata["articles"] for c in chunks]


def test_an_annex_header_ends_the_open_article():
    assert _tag("Artículo 69\nEntrada en vigor", "ANEXO I\nVariables de riesgo") == [[69], []]


def test_everything_after_the_first_annex_is_not_an_article_even_if_it_repeats_article_lines():
    # Annexes follow all the articles; the correspondence table repeats "Artículo N" lines.
    tags = _tag(
        "Artículo 68\nuno",
        "L 141/113\nANEXO I\nlista",
        "continúa el anexo",
        "Artículo 22 Artículo 2, apartado 4\nArtículo 25 Artículo 14",
    )
    assert tags == [[68], [], [], []]


def test_a_chunk_that_mixes_the_last_article_and_the_annex_counts_as_annex():
    assert _tag("Artículo 9\nuno", "fin del 9\nANEXO II\ntexto") == [[9], []]


def test_a_lowercase_reference_to_an_annex_is_not_an_annex_header():
    assert _tag("Artículo 9\nconforme al anexo I de la Directiva", "continúa") == [[9], [9]]


def test_4amld_annexes_and_correspondence_table_are_never_tagged_as_articles():
    chunks = split_into_chunks(PDFPlumberLoader(str(REPO_ROOT / "data" / "CELEX_32015L0849_ES_TXT.pdf")).load())
    first_annex = next(i for i, c in enumerate(chunks) if ANNEX_HEADER_RE.search(c.page_content))
    assert all(not c.metadata["articles"] for c in chunks[first_annex:])
    # and the articles before it are still tagged, e.g. the chunk that opens Article 11
    assert any(11 in c.metadata["articles"] for c in chunks[:first_annex])
