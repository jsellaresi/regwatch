import logging

from retriever import get_hybrid_retriever
from graph.state import RegWatchState

logger = logging.getLogger(__name__)


def retrieve_regulations(state: RegWatchState) -> dict:
    query = state["extracted_text"][:2000]
    docs = get_hybrid_retriever().invoke(query)
    logger.info("retrieve_regulations: %d docs retrieved", len(docs))
    return {
        "retrieved_regulations": [
            {
                "content": d.page_content,
                "regulation": d.metadata.get("regulation", "unknown"),
                "celex": d.metadata.get("celex", ""),
                "source_url": d.metadata.get("source_url", ""),
            }
            for d in docs
        ]
    }
