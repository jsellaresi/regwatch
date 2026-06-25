from langchain_cohere import CohereRerank
from langchain_core.documents import Document
from graph.state import RegWatchState
from config import COHERE_API_KEY

reranker = CohereRerank(model="rerank-multilingual-v3.0",
                        top_n=5, cohere_api_key=COHERE_API_KEY)


def rerank(state: RegWatchState) -> dict:
    query = state["extracted_text"][:2000]
    docs = [
        Document(page_content=r["content"], metadata=r)
        for r in state["retrieved_regulations"]
    ]
    top = reranker.compress_documents(documents=docs, query=query)
    return {"retrieved_regulations": [d.metadata | {"content": d.page_content} for d in top]}

# ── Alternativa 100% local (sin coste por llamada, requiere torch + sentence-transformers) ──
# from sentence_transformers import CrossEncoder
# _ce = CrossEncoder("BAAI/bge-reranker-v2-m3")
# scores = _ce.predict([(query, r["content"]) for r in state["retrieved_regulations"]])
# top = [r for _, r in sorted(zip(scores, regs), key=lambda x: x[0], reverse=True)][:5]
