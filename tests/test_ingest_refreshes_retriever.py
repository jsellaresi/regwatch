import asyncio
import json

import retriever
from api import main


def _drain_ingest(monkeypatch, ingest_fn):
    monkeypatch.setattr(main, "REGULATIONS", [("a.pdf", "GDPR"), ("b.pdf", "MiFID II")])
    monkeypatch.setattr(main, "ingest_regulation", ingest_fn)
    events = []

    async def run():
        response = await main.ingest()
        async for event in response.body_iterator:
            events.append(event)

    asyncio.run(run())
    return events


def test_ingest_invalidates_cached_hybrid_retriever(monkeypatch):
    monkeypatch.setattr(retriever, "_hybrid_retriever", object())
    _drain_ingest(monkeypatch, lambda *args: None)
    assert retriever._hybrid_retriever is None


def test_refresh_runs_before_done_event(monkeypatch):
    order = []
    monkeypatch.setattr(main, "refresh_hybrid_retriever", lambda: order.append("refresh"))
    events = _drain_ingest(monkeypatch, lambda *args: order.append("ingest"))
    done_idx = next(i for i, e in enumerate(events) if "completada" in json.dumps(getattr(e, "data", e)))
    assert order == ["ingest", "ingest", "refresh"]
    assert done_idx == len(events) - 1
