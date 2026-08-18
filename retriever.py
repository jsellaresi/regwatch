import logging

from config import DATABASE_URL, MODEL_EMBEDDINGS

logger = logging.getLogger(__name__)

_hybrid_retriever = None


def _load_chunks_from_db(engine) -> list:
    from langchain_core.documents import Document
    from sqlalchemy import text

    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT document, cmetadata FROM langchain_pg_embedding"
        )).fetchall()
    docs = [Document(page_content=r[0], metadata=r[1] or {}) for r in rows]
    logger.info("_load_chunks_from_db: %d documents loaded", len(docs))
    return docs


def _build_hybrid_retriever():
    from langchain_openai import OpenAIEmbeddings
    from langchain_community.vectorstores import PGVector
    from langchain_community.retrievers import BM25Retriever
    from langchain_classic.retrievers import EnsembleRetriever
    from sqlalchemy import create_engine

    embeddings = OpenAIEmbeddings(model=MODEL_EMBEDDINGS)
    vectorstore = PGVector(
        connection_string=DATABASE_URL,
        embedding_function=embeddings,
        collection_name="regulations",
    )
    semantic = vectorstore.as_retriever(search_kwargs={"k": 20})

    chunks = _load_chunks_from_db(create_engine(DATABASE_URL))
    if not chunks:
        logger.warning("No regulation chunks in DB — using semantic-only retrieval")
        return semantic

    bm25 = BM25Retriever.from_documents(chunks)
    bm25.k = 20
    return EnsembleRetriever(retrievers=[semantic, bm25], weights=[0.5, 0.5])


def get_hybrid_retriever():
    """Lazily build the hybrid (semantic + BM25) retriever on first real use.
    Importing this module must not run a DB query or construct a vector store
    — that only makes sense once DATABASE_URL is actually reachable."""
    global _hybrid_retriever
    if _hybrid_retriever is None:
        _hybrid_retriever = _build_hybrid_retriever()
    return _hybrid_retriever


def refresh_hybrid_retriever():
    """Force a rebuild on next get_hybrid_retriever() call — e.g. after /ingest
    adds new regulation chunks, so BM25 doesn't stay stale until a restart."""
    global _hybrid_retriever
    _hybrid_retriever = None
