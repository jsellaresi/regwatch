"""Transient in-memory holder for uploaded PDF bytes, keyed by sha256.

Keeps the PDF out of the LangGraph state, which the checkpointer persists.
Entries expire after TTL_SECONDS and are not dropped on read, so concurrent
analyses of the same file don't pull the bytes from under each other.
"""
import hashlib
import time

TTL_SECONDS = 10 * 60

_store: dict[str, tuple[float, bytes]] = {}


def _evict_expired() -> None:
    now = time.monotonic()
    for key in [k for k, (ts, _) in _store.items() if now - ts > TTL_SECONDS]:
        del _store[key]


def put(data: bytes) -> str:
    _evict_expired()
    doc_hash = hashlib.sha256(data).hexdigest()
    _store[doc_hash] = (time.monotonic(), data)
    return doc_hash


def get(doc_hash: str) -> bytes:
    _evict_expired()
    try:
        return _store[doc_hash][1]
    except KeyError:
        raise LookupError(
            f"Uploaded document {doc_hash[:12]} is no longer available "
            "(expired or the API restarted); upload it again."
        ) from None
