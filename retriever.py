from langchain_openai import OpenAIEmbeddings
from langchain_community.vectorstores import PGVector
from langchain_community.retrievers import BM25Retriever
from langchain.retrievers import EnsembleRetriever
from langchain_core.documents import Document
from sqlalchemy import create_engine, text
from config import DATABASE_URL

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")


def _load_chunks_from_db() -> list[Document]:
    engine = create_engine(DATABASE_URL)
    with engine.connect() as conn:
        rows = conn.execute(text(
            "SELECT document, cmetadata FROM langchain_pg_embedding"
        )).fetchall()
    return [Document(page_content=r[0], metadata=r[1] or {}) for r in rows]


_vectorstore = PGVector(
    connection_string=DATABASE_URL,
    embedding_function=embeddings,
    collection_name="regulations",
)
_semantic = _vectorstore.as_retriever(search_kwargs={"k": 20})
_bm25 = BM25Retriever.from_documents(_load_chunks_from_db())
_bm25.k = 20

HYBRID_RETRIEVER = EnsembleRetriever(
    retrievers=[_semantic, _bm25],
    weights=[0.5, 0.5],
)
