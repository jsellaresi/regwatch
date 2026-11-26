import asyncio
import time
from types import SimpleNamespace

import httpx

import config
from api import main


class _SlowAsyncLLM:
    """Only exposes ainvoke: a blocking invoke() would fail the test."""

    def __init__(self, delay):
        self.delay = delay
        self.calls = 0

    async def ainvoke(self, messages):
        self.calls += 1
        await asyncio.sleep(self.delay)
        return SimpleNamespace(content="respuesta")

    def invoke(self, messages):
        raise AssertionError("/chat must not call the blocking invoke()")


class _Graph:
    async def aget_state(self, config):
        return SimpleNamespace(values={"final_report": {"gaps": []}})


def _setup(monkeypatch, llm):
    monkeypatch.setattr(config, "API_KEY", "k")
    monkeypatch.setattr(main, "get_graph", lambda: _Graph())
    monkeypatch.setattr(main, "_get_chat_llm", lambda: llm)
    main.SESSION_BUFFER.clear()


async def _post(client, thread_id):
    return await client.post(
        "/chat", headers={"X-API-Key": "k"}, data={"thread_id": thread_id, "question": "¿Qué gaps hay?"}
    )


def test_chat_uses_the_async_client_and_returns_the_answer(monkeypatch):
    llm = _SlowAsyncLLM(delay=0)
    _setup(monkeypatch, llm)

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as client:
            return await _post(client, "t1")

    response = asyncio.run(go())
    assert response.status_code == 200 and response.json() == {"answer": "respuesta"}
    assert llm.calls == 1


def test_two_concurrent_chats_overlap_instead_of_blocking_the_event_loop(monkeypatch):
    llm = _SlowAsyncLLM(delay=0.4)
    _setup(monkeypatch, llm)

    async def go():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://t") as client:
            started = time.perf_counter()
            await asyncio.gather(_post(client, "a"), _post(client, "b"))
            return time.perf_counter() - started

    elapsed = asyncio.run(go())
    assert llm.calls == 2
    assert elapsed < 0.7, f"chats ran one after the other ({elapsed:.2f}s): the event loop was blocked"


def test_the_chat_client_is_built_once_and_reused(monkeypatch):
    built = []

    class _Client:
        def __init__(self, **kwargs):
            built.append(kwargs)

    monkeypatch.setattr(main, "ChatOpenAI", _Client)
    monkeypatch.setattr(main, "_chat_llm", None)
    first, second = main._get_chat_llm(), main._get_chat_llm()
    assert first is second and len(built) == 1
    monkeypatch.setattr(main, "_chat_llm", None)
