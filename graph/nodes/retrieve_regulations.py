from retriever import HYBRID_RETRIEVER
from graph.state import RegWatchState


def retrieve_regulations(state: RegWatchState) -> dict:
    query = state["extracted_text"][:2000]
    docs = HYBRID_RETRIEVER.invoke(query)
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
