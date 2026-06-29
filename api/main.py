import json
import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sse_starlette.sse import EventSourceResponse
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from graph import get_graph, init_graph
from scripts.register_prompts import ensure_prompts
from scripts.ingest_regulations import ingest_regulation, REGULATIONS

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_prompts()
    await init_graph()
    logger.info("RegWatch graph initialized")
    yield


app = FastAPI(title="RegWatch API", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

SESSION_BUFFER: dict[str, list] = {}


@app.post("/analyze")
async def analyze_document(file: UploadFile, policy_id: str = Form(...)):
    graph = get_graph()
    document_bytes = await file.read()
    logger.info("analyze: policy_id=%s file=%s size=%d bytes", policy_id, file.filename, len(document_bytes))
    config = {"configurable": {"thread_id": f"{policy_id}:{file.filename}"}}
    result = graph.invoke(
        {
            "document_bytes": document_bytes,
            "document_name": file.filename,
            "policy_id": policy_id,
            "judge_attempt": 0,
            "output_guardrail_attempt": 0,
        },
        config=config,
    )
    logger.info("analyze complete: policy_id=%s", policy_id)
    return result["final_report"]


@app.post("/analyze/stream")
async def analyze_stream(file: UploadFile, policy_id: str = Form(...), thread_id: str = Form(None)):
    document_bytes = await file.read()
    if not thread_id:
        thread_id = f"{policy_id}:{file.filename}"
    logger.info("analyze/stream: policy_id=%s file=%s thread_id=%s", policy_id, file.filename, thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    init = {
        "document_bytes": document_bytes,
        "document_name": file.filename,
        "policy_id": policy_id,
        "judge_attempt": 0,
        "output_guardrail_attempt": 0,
    }
    graph = get_graph()

    async def event_generator():
        try:
            async for chunk in graph.astream(init, config=config, stream_mode="updates"):
                for node_name, node_output in chunk.items():
                    if node_name == "__interrupt__":
                        logger.info("stream: human review triggered thread_id=%s", thread_id)
                        interrupts = node_output if isinstance(node_output, (list, tuple)) else [node_output]
                        payload = interrupts[0].value if hasattr(interrupts[0], "value") else {}
                        # Mark the HITL step as reached in the pipeline before signalling review
                        yield {"event": "node", "data": json.dumps({"node": "human_review_checkpoint"})}
                        yield {"event": "needs_review", "data": json.dumps(payload)}
                    else:
                        logger.info("stream: node=%s thread_id=%s", node_name, thread_id)
                        yield {"event": "node", "data": json.dumps({"node": node_name})}
            logger.info("stream: pipeline complete, fetching final state thread_id=%s", thread_id)
            state = await graph.aget_state(config)
            final = state.values.get("final_report", {})
            if final:
                logger.info("stream: done event thread_id=%s has_report=True", thread_id)
                yield {"event": "done", "data": json.dumps(final)}
            else:
                logger.info("stream: pipeline paused at HITL, no done event thread_id=%s", thread_id)
        except Exception:
            logger.exception("stream: event_generator error thread_id=%s", thread_id)
            yield {"event": "error", "data": json.dumps({"error": "pipeline failed"})}

    return EventSourceResponse(event_generator())


@app.post("/resume")
async def resume(thread_id: str = Form(...), decision: str = Form(...)):
    logger.info("resume: thread_id=%s decision=%s", thread_id, decision)
    config = {"configurable": {"thread_id": thread_id}}
    result = await get_graph().ainvoke(Command(resume=decision), config=config)
    if result.get("final_report"):
        logger.info("resume: completed thread_id=%s", thread_id)
        return {"status": "done", "final_report": result["final_report"]}
    # Reject path: re-analysis ran and HITL triggered again
    state = await get_graph().aget_state(config)
    interrupts = [i for task in (state.tasks or []) for i in getattr(task, "interrupts", [])]
    if interrupts:
        payload = interrupts[0].value if hasattr(interrupts[0], "value") else {}
        logger.info("resume: re-interrupted thread_id=%s", thread_id)
        return {"status": "needs_review", **payload}
    logger.warning("resume: unexpected state thread_id=%s", thread_id)
    return {"status": "running"}


@app.get("/state/{thread_id}")
async def get_state(thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    try:
        state = await get_graph().aget_state(config)
    except Exception:
        return None
    if not state or not state.values:
        return None  # thread never started
    if state.values.get("final_report"):
        return {"status": "completed", **state.values["final_report"]}
    interrupts = [i for task in (state.tasks or []) for i in getattr(task, "interrupts", [])]
    if interrupts:
        payload = interrupts[0].value if hasattr(interrupts[0], "value") else {}
        return {"status": "needs_review", **payload}
    # Checkpoint exists with partial state but no active tasks — run was aborted (e.g. container restart)
    if state.tasks is not None and len(state.tasks) == 0:
        logger.warning("get_state: aborted thread_id=%s", thread_id)
        return {"status": "aborted"}
    return None  # tasks pending but not yet checkpointed (still running)


@app.post("/ingest")
async def ingest():
    """Stream ingestion progress as Server-Sent Events."""
    async def event_gen():
        import asyncio
        for args in REGULATIONS:
            name = args[1]
            try:
                await asyncio.get_event_loop().run_in_executor(None, lambda a=args: ingest_regulation(*a))
                yield {"event": "progress", "data": json.dumps({"regulation": name, "status": "ok"})}
            except Exception as exc:
                logger.exception("ingest: failed %s", name)
                yield {"event": "progress", "data": json.dumps({"regulation": name, "status": "error", "detail": str(exc)})}
        yield {"event": "done", "data": json.dumps({"message": "Ingesta completada", "total": len(REGULATIONS)})}
    return EventSourceResponse(event_gen())


@app.post("/chat")
async def chat(thread_id: str = Form(...), question: str = Form(...)):
    logger.info("chat: thread_id=%s", thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    report = (await get_graph().aget_state(config)).values.get("final_report", {})
    history = SESSION_BUFFER.setdefault(thread_id, [])
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = (f"Informe de compliance:\n{json.dumps(report, ensure_ascii=False)}\n\n"
              f"Historial:\n{history}\n\nPregunta: {question}")
    answer = llm.invoke(prompt).content
    history.append((question, answer))
    return {"answer": answer}
