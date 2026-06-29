import logging

from langchain_openai import OpenAIEmbeddings
from config import MODEL_EMBEDDINGS
from langchain_community.vectorstores import PGVector
from langchain_community.retrievers import BM25Retriever
from langchain_classic.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from sqlalchemy import create_engine, text
from config import DATABASE_URL

logger = logging.getLogger(__name__)

embeddings = OpenAIEmbeddings(model=MODEL_EMBEDDINGS)


def _load_chunks_from_db() -> list[Document]:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT document, cmetadata FROM langchain_pg_embedding"
        )).fetchall()
    docs = [Document(page_content=r[0], metadata=r[1] or {}) for r in rows]
    logger.info("_load_chunks_from_db: %d documents loaded", len(docs))
    return docs


_vectorstore = PGVector(
    connection_string=DATABASE_URL,
    embedding_function=embeddings,
    collection_name="regulations",
)
_semantic = _vectorstore.as_retriever(search_kwargs={"k": 20})

_chunks = _load_chunks_from_db()
if _chunks:
    _bm25 = BM25Retriever.from_documents(_chunks)
    _bm25.k = 20
    HYBRID_RETRIEVER = EnsembleRetriever(
        retrievers=[_semantic, _bm25],
        weights=[0.5, 0.5],
    )
else:
    logger.warning("No regulation chunks in DB — using semantic-only retrieval")
    HYBRID_RETRIEVER = _semantic
