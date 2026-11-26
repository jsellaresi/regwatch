import logging

from langchain_core.documents import Document
from graph.state import RegWatchState
from config import COHERE_API_KEY, MODEL_RERANK_COHERE, MODEL_RERANK_LOCAL

try:
    from cohere.errors.unauthorized_error import UnauthorizedError as _CohereUnauthorized
except ImportError:
    _CohereUnauthorized = Exception

logger = logging.getLogger(__name__)

TOP_N = 8  # keep REG_CONTEXT_CHARS (config.py) large enough for TOP_N chunks

_local_ce = None
_cohere = None


def _get_local_ce():
    """Lazily load the local cross-encoder — this downloads/loads a model
    file, so it must only happen on first real use, and only when Cohere
    isn't configured (or as its fallback), not unconditionally at import."""
    global _local_ce
    if _local_ce is None:
        from sentence_transformers import CrossEncoder

        logger.info("rerank: cargando cross-encoder local %s", MODEL_RERANK_LOCAL)
        _local_ce = CrossEncoder(MODEL_RERANK_LOCAL)
    return _local_ce


def _get_cohere():
    global _cohere
    if _cohere is None:
        from langchain_cohere import CohereRerank

        _cohere = CohereRerank(model=MODEL_RERANK_COHERE,
                               top_n=TOP_N, cohere_api_key=COHERE_API_KEY)
    return _cohere


def _citable(regs: list[dict]) -> list[dict]:
    """Drop chunks that belong to no article (recitals, annexes): they cannot ground a
    "Reg Art. N" citation yet used to take top-N slots from the articles themselves.
    Chunks without the `articles` tag at all (corpus ingested before tagging) are kept,
    and so is everything if nothing citable was retrieved."""
    citable = [r for r in regs if r.get("articles") != []]
    return citable or regs


def rerank(state: RegWatchState) -> dict:
    query = state["extracted_text"][:2000]
    regs = _citable(state["retrieved_regulations"])

    if COHERE_API_KEY:
        docs = [Document(page_content=r["content"], metadata=r) for r in regs]
        try:
            top_docs = _get_cohere().compress_documents(documents=docs, query=query)
            top = [d.metadata | {"content": d.page_content} for d in top_docs]
        except _CohereUnauthorized:
            logger.warning("rerank: Cohere key inválida, usando cross-encoder local como fallback")
            scores = _get_local_ce().predict([(query, r["content"]) for r in regs])
            ranked = sorted(zip(scores, regs), key=lambda x: x[0], reverse=True)
            top = [r for _, r in ranked[:TOP_N]]
    else:
        scores = _get_local_ce().predict([(query, r["content"]) for r in regs])
        ranked = sorted(zip(scores, regs), key=lambda x: x[0], reverse=True)
        top = [r for _, r in ranked[:TOP_N]]

    logger.info("rerank: %d → %d docs", len(regs), len(top))
    return {"retrieved_regulations": top}
