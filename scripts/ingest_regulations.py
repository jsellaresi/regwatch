import logging
import os

from langchain_community.document_loaders import PDFPlumberLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings
from config import MODEL_EMBEDDINGS
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
        conn.execute(text(HNSW_INDEX_SQL))
        conn.commit()
    logger.info("HNSW index ensured on langchain_pg_embedding")


def ingest_regulation(pdf_path: str, regulation_name: str,
                      celex: str, source_url: str, version_date: str):
    loader = PDFPlumberLoader(pdf_path)
    raw_docs = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=800,
        chunk_overlap=100,
        separators=["\nArtículo", "\nArticle", "\n\n", "\n"],
    )
    chunks = splitter.split_documents(raw_docs)

    for chunk in chunks:
        chunk.metadata.update({
            "regulation": regulation_name,
            "celex": celex,
            "source_url": source_url,
            "version_date": version_date,
            "language": "ES",
        })

    embeddings = OpenAIEmbeddings(model=MODEL_EMBEDDINGS)
    PGVector.from_documents(
        documents=chunks,
        embedding=embeddings,
        collection_name="regulations",
        connection_string=CONNECTION_STRING,
    )
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
