import json
import logging
from contextlib import asynccontextmanager

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
)
from fastapi import FastAPI, UploadFile, Form
from fastapi.middleware.cors import CORSMiddleware
from sse_starlette.sse import EventSourceResponse
from langgraph.types import Command
from langchain_openai import ChatOpenAI
from graph import get_graph, init_graph
from scripts.register_prompts import ensure_prompts

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
async def analyze_stream(file: UploadFile, policy_id: str = Form(...)):
    document_bytes = await file.read()
    thread_id = f"{policy_id}:{file.filename}"
    logger.info("analyze/stream: policy_id=%s file=%s", policy_id, file.filename)
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
        async for chunk in graph.astream(init, config=config, stream_mode="updates"):
            for node_name, node_output in chunk.items():
                yield {"event": "node", "data": json.dumps({"node": node_name})}
                if node_name == "__interrupt__":
                    logger.info("stream: human review triggered thread_id=%s", thread_id)
                    yield {"event": "needs_review", "data": json.dumps(node_output)}
        final = graph.get_state(config).values.get("final_report", {})
        yield {"event": "done", "data": json.dumps(final)}

    return EventSourceResponse(event_generator())


@app.post("/resume")
async def resume(thread_id: str = Form(...), decision: str = Form(...)):
    logger.info("resume: thread_id=%s decision=%s", thread_id, decision)
    config = {"configurable": {"thread_id": thread_id}}
    result = get_graph().invoke(Command(resume=decision), config=config)
    return result["final_report"]


@app.post("/chat")
async def chat(thread_id: str = Form(...), question: str = Form(...)):
    logger.info("chat: thread_id=%s", thread_id)
    config = {"configurable": {"thread_id": thread_id}}
    report = get_graph().get_state(config).values.get("final_report", {})
    history = SESSION_BUFFER.setdefault(thread_id, [])
    llm = ChatOpenAI(model="gpt-4o", temperature=0)
    prompt = (f"Informe de compliance:\n{json.dumps(report, ensure_ascii=False)}\n\n"
              f"Historial:\n{history}\n\nPregunta: {question}")
    answer = llm.invoke(prompt).content
    history.append((question, answer))
    return {"answer": answer}
