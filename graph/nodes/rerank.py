import logging

from langchain_core.documents import Document
from graph.state import RegWatchState
from config import COHERE_API_KEY

try:
    from cohere.errors.unauthorized_error import UnauthorizedError as _CohereUnauthorized
except ImportError:
    _CohereUnauthorized = Exception

logger = logging.getLogger(__name__)

TOP_N = 5

from sentence_transformers import CrossEncoder
_local_ce = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")

if COHERE_API_KEY:
    from langchain_cohere import CohereRerank
    _cohere = CohereRerank(model="rerank-multilingual-v3.0",
                           top_n=TOP_N, cohere_api_key=COHERE_API_KEY)
    logger.info("rerank: usando Cohere rerank-multilingual-v3.0")
else:
    logger.info("rerank: usando local cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank(state: RegWatchState) -> dict:
    query = state["extracted_text"][:2000]
    regs = state["retrieved_regulations"]

    if COHERE_API_KEY:
        docs = [Document(page_content=r["content"], metadata=r) for r in regs]
        try:
            top_docs = _cohere.compress_documents(documents=docs, query=query)
            top = [d.metadata | {"content": d.page_content} for d in top_docs]
        except _CohereUnauthorized:
            logger.warning("rerank: Cohere key inválida, usando cross-encoder local como fallback")
            scores = _local_ce.predict([(query, r["content"]) for r in regs])
            ranked = sorted(zip(scores, regs), key=lambda x: x[0], reverse=True)
            top = [r for _, r in ranked[:TOP_N]]
    else:
        scores = _local_ce.predict([(query, r["content"]) for r in regs])
        ranked = sorted(zip(scores, regs), key=lambda x: x[0], reverse=True)
        top = [r for _, r in ranked[:TOP_N]]

    logger.info("rerank: %d → %d docs", len(regs), len(top))
    return {"retrieved_regulations": top}
