import logging

from langchain_text_splitters import RecursiveCharacterTextSplitter
from retriever import get_hybrid_retriever
from graph.state import RegWatchState

logger = logging.getLogger(__name__)

MAX_QUERY_CHARS = 2000  # bound on any single retrieval query (matches prior single-query behavior)
MIN_SECTION_CHARS = 200  # skip near-empty sections (headers, stray whitespace) as their own query
MAX_SECTIONS = 8  # cap retrieval calls per analysis — cost/latency bound, not a correctness limit

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=100,
    separators=["\nSección", "\nSection", "\nCláusula", "\nClause", "\n\n", "\n"],
)


def _split_into_queries(extracted_text: str) -> list[str]:
    """Split the policy document into section/clause-sized queries instead of
    using a single extracted_text[:2000] blob as the only query. A policy
    mixing GDPR/MiFID/AML topics across different sections can lose recall
    when compressed into one query — relevant text past the 2000-char mark,
    or in a later section entirely, never gets a chance to retrieve anything
    (see docs/ADR-0003-hybrid-retrieval.md).

    A document short enough to fit in one query is returned as exactly one
    query — unchanged behavior for short documents.
    """
    if not extracted_text.strip():
        return []
    if len(extracted_text) <= MAX_QUERY_CHARS:
        return [extracted_text]
    sections = _splitter.split_text(extracted_text)
    queries = [s[:MAX_QUERY_CHARS] for s in sections if len(s.strip()) >= MIN_SECTION_CHARS]
    return queries[:MAX_SECTIONS] or [extracted_text[:MAX_QUERY_CHARS]]


def _dedup(docs: list) -> list:
    """Collapse documents retrieved by multiple section-queries down to one
    entry per unique (regulation, content) pair, preserving first-seen order."""
    seen = set()
    unique = []
    for d in docs:
        key = (d.metadata.get("regulation", ""), d.page_content)
        if key not in seen:
            seen.add(key)
            unique.append(d)
    return unique


def retrieve_regulations(state: RegWatchState) -> dict:
    queries = _split_into_queries(state["extracted_text"])
    retriever = get_hybrid_retriever()
    all_docs = []
    for query in queries:
        all_docs.extend(retriever.invoke(query))
    docs = _dedup(all_docs)
    logger.info(
        "retrieve_regulations: %d quer%s -> %d docs after dedup (%d raw)",
        len(queries), "y" if len(queries) == 1 else "ies", len(docs), len(all_docs),
    )
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
