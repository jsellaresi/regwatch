import logging

from langchain_core.documents import Document
from graph.state import RegWatchState
from config import COHERE_API_KEY

logger = logging.getLogger(__name__)

TOP_N = 5

if COHERE_API_KEY:
    from langchain_cohere import CohereRerank
    _cohere = CohereRerank(model="rerank-multilingual-v3.0",
                           top_n=TOP_N, cohere_api_key=COHERE_API_KEY)
    logger.info("rerank: usando Cohere rerank-multilingual-v3.0")
else:
    from sentence_transformers import CrossEncoder
    _local_ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")
    logger.info("rerank: usando local cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(state: RegWatchState) -> dict:
    query = state["extracted_text"][:2000]
    regs = state["retrieved_regulations"]

    if COHERE_API_KEY:
        docs = [Document(page_content=r["content"], metadata=r) for r in regs]
        top_docs = _cohere.compress_documents(documents=docs, query=query)
        top = [d.metadata | {"content": d.page_content} for d in top_docs]
    else:
        scores = _local_ce.predict([(query, r["content"]) for r in regs])
        ranked = sorted(zip(scores, regs), key=lambda x: x[0], reverse=True)
        top = [r for _, r in ranked[:TOP_N]]

    logger.info("rerank: %d → %d docs", len(regs), len(top))
    return {"retrieved_regulations": top}
