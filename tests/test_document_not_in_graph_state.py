import hashlib
import importlib
import types
from typing import get_type_hints

import pytest

import document_store
from graph.state import RegWatchState

mx = importlib.import_module("graph.nodes.multimodal_extract")


def test_state_no_longer_carries_pdf_bytes_or_page_images():
    fields = get_type_hints(RegWatchState)
    assert "document_bytes" not in fields
    assert "extracted_images" not in fields
    assert "doc_hash" in fields


def test_put_returns_sha256_and_get_returns_the_bytes():
    data = b"%PDF-1.7 fake"
    doc_hash = document_store.put(data)
    assert doc_hash == hashlib.sha256(data).hexdigest()
    assert document_store.get(doc_hash) == data
    assert document_store.get(doc_hash) == data  # not dropped on read


def test_get_raises_clear_error_for_unknown_or_expired_hash(monkeypatch):
    with pytest.raises(LookupError, match="upload it again"):
        document_store.get("0" * 64)

    doc_hash = document_store.put(b"short lived")
    monkeypatch.setattr(document_store, "TTL_SECONDS", -1)
    with pytest.raises(LookupError):
        document_store.get(doc_hash)


class _FakePage:
    def __init__(self, text):
        self._text = text

    def get_text(self):
        return self._text


def test_multimodal_extract_reads_bytes_from_store_and_returns_no_images(monkeypatch):
    doc_hash = document_store.put(b"pdf bytes")
    seen = {}

    def fake_open(stream, filetype):
        seen["stream"] = stream
        return [_FakePage("Política de retención de datos")]

    monkeypatch.setattr(mx.fitz, "open", fake_open)
    monkeypatch.setattr(mx, "get_langfuse", lambda: types.SimpleNamespace(get_trace_url=lambda: "http://trace"))

    out = mx.multimodal_extract({"doc_hash": doc_hash, "document_name": "p.pdf"})

    assert seen["stream"] == b"pdf bytes"
    assert set(out) == {"extracted_text", "trace_url"}
    assert "Política de retención" in out["extracted_text"]
