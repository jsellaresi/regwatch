import logging
import os
import re

from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from config import EMBEDDING_DIMENSIONS, MODEL_EMBEDDINGS
from langchain_community.vectorstores import PGVector
from sqlalchemy import create_engine, text
from cache_invalidation import invalidate_analysis_cache

logger = logging.getLogger(__name__)

CONNECTION_STRING = os.getenv("DATABASE_URL", "postgresql+psycopg2://regwatch:regwatch@db:5432/regwatch")

# ADR-0004's decision. Kept as a named-index DDL statement (not the unnamed
# `CREATE INDEX ON ...` shorthand in the ADR text) because `IF NOT EXISTS`
# requires an explicit name in Postgres.
HNSW_INDEX_SQL = (
    "CREATE INDEX IF NOT EXISTS idx_langchain_pg_embedding_hnsw "
    "ON langchain_pg_embedding "
    "USING hnsw (embedding vector_cosine_ops) "
    "WITH (m = 16, ef_construction = 64)"
)

# Scoped to one regulation: all five live in the same "regulations" collection,
# so PGVector's pre_delete_collection=True would wipe the other four.
DELETE_STALE_CHUNKS_SQL = (
    "DELETE FROM langchain_pg_embedding "
    "WHERE cmetadata->>'celex' = :celex "
    "AND (custom_id IS NULL OR custom_id <> ALL(:new_ids)) "
    "AND collection_id IN (SELECT uuid FROM langchain_pg_collection WHERE name = 'regulations')"
)


# langchain's PGVector creates `embedding` as an untyped `vector` (atttypmod -1),
# and pgvector refuses to index a column without dimensions ("column does not
# have dimensions"), so the column has to be typed before the index exists.
EMBEDDING_TYPMOD_SQL = (
    "SELECT atttypmod FROM pg_attribute "
    "WHERE attrelid = 'langchain_pg_embedding'::regclass AND attname = 'embedding'"
)
SET_EMBEDDING_DIMENSIONS_SQL = (
    f"ALTER TABLE langchain_pg_embedding ALTER COLUMN embedding TYPE vector({EMBEDDING_DIMENSIONS})"
)


def _ensure_hnsw_index(connection_string: str) -> None:
    """Create the HNSW index ADR-0004 specifies, once langchain_pg_embedding
    actually exists. This can't live in docker/init-db.sql: that script only
    runs once, on first container init, before the app has ever created its
    own tables via PGVector — a CREATE INDEX there would fail outright on a
    fresh volume, or (if guarded to skip a missing table) silently never run
    at all, since init-db.sql never fires again afterwards. Idempotent, so
    it's safe to call after every ingestion."""
    engine = create_engine(connection_string)
    with engine.connect() as conn:
        if conn.execute(text(EMBEDDING_TYPMOD_SQL)).scalar() == -1:
            conn.execute(text(SET_EMBEDDING_DIMENSIONS_SQL))
        conn.execute(text(HNSW_INDEX_SQL))
        conn.commit()
    logger.info("HNSW index ensured on langchain_pg_embedding")


def _delete_stale_chunks(connection_string: str, celex: str, new_ids: list[str]) -> int:
    """Remove this regulation's chunks from previous ingestions, keeping the
    ones just inserted. Runs after the insert so a failed embedding call
    leaves the old corpus intact rather than an empty one."""
    if not new_ids:
        return 0
    engine = create_engine(connection_string)
    with engine.begin() as conn:
        return conn.execute(text(DELETE_STALE_CHUNKS_SQL), {"celex": celex, "new_ids": new_ids}).rowcount


ARTICLE_HEADER_RE = re.compile(r"(?m)^\s*Art[ií]culo\s+(\d+)\b")


def tag_articles(chunks) -> None:
    """Record in `metadata["articles"]` which article(s) each chunk belongs to.

    A long article is split into several chunks and only the first one starts with
    its "Artículo N" header; without this, the chunk that holds e.g. GDPR 5(1)(e)
    could not be traced back to Article 5. Chunks are visited in document order: a
    chunk inherits the article opened before it, plus any header that starts a line
    inside it (small adjacent articles can share a chunk). Text before the first
    article (recitals) gets an empty list."""
    current = None
    for chunk in chunks:
        headers = [int(n) for n in ARTICLE_HEADER_RE.findall(chunk.page_content)]
        opens_with_header = ARTICLE_HEADER_RE.match(chunk.page_content) is not None
        inherited = [current] if current is not None and not opens_with_header else []
        chunk.metadata["articles"] = inherited + headers
        if headers:
            current = headers[-1]


def split_into_chunks(raw_docs) -> list:
    """Split loaded PDF pages into chunks (one natural break per article) and tag
    each chunk with the article(s) it belongs to."""
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\nArtículo", "\nArticle", "\n\n", "\n"],
    )
    chunks = splitter.split_documents(raw_docs)
    tag_articles(chunks)
    return chunks


def ingest_regulation(pdf_path: str, regulation_name: str,
                      celex: str, source_url: str, version_date: str):
    loader = PDFPlumberLoader(pdf_path)
    chunks = split_into_chunks(loader.load())

    for chunk in chunks:
        chunk.metadata.update({
            "regulation": regulation_name,
            "celex": celex,
            "source_url": source_url,
            "version_date": version_date,
            "language": "ES",
        })

    embeddings = OpenAIEmbeddings(model=MODEL_EMBEDDINGS)
    store = PGVector(
        connection_string=CONNECTION_STRING,
        embedding_function=embeddings,
        collection_name="regulations",
    )
    new_ids = store.add_documents(chunks)
    removed = _delete_stale_chunks(CONNECTION_STRING, celex, new_ids)
    logger.info("Removed %d stale chunks of %s from earlier ingestions", removed, regulation_name)
    _ensure_hnsw_index(CONNECTION_STRING)
    # ADR-0006: a cached report may cite text from this regulation's previous
    # version — clear it rather than risk serving a gap analysis against a
    # since-amended article.
    invalidate_analysis_cache(reason=f"regulation re-ingested: {regulation_name} ({celex})")
    logger.info("Ingestados %d chunks de %s (%s)", len(chunks), regulation_name, celex)


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    regulations = REGULATIONS
    for args in regulations:
        ingest_regulation(*args)


REGULATIONS = [
    ("data/CELEX_32016R0679_ES_TXT.pdf", "GDPR", "32016R0679",
     "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32016R0679", "2016-05-04"),
    ("data/CELEX_32014L0065_ES_TXT.pdf", "MiFID II", "32014L0065",
     "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32014L0065", "2014-05-15"),
    ("data/CELEX_32015L0849_ES_TXT.pdf", "4AMLD", "32015L0849",
     "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32015L0849", "2015-05-20"),
    ("data/CELEX_32018L0843_ES_TXT.pdf", "5AMLD", "32018L0843",
     "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32018L0843", "2018-05-30"),
    ("data/CELEX_32018L1673_ES_TXT.pdf", "6AMLD", "32018L1673",
     "https://eur-lex.europa.eu/legal-content/ES/TXT/PDF/?uri=CELEX:32018L1673", "2018-10-23"),
]


if __name__ == "__main__":
    main()
