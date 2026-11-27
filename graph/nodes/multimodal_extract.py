import logging
import fitz
import base64
from langchain_anthropic import ChatAnthropic
from config import MODEL_VISION
from langchain_core.messages import HumanMessage
from langfuse import observe
from config import get_langfuse
from graph.llm_text import message_text
from graph.state import RegWatchState
import document_store

logger = logging.getLogger(__name__)

_llm_vision = None


def _get_llm_vision():
    global _llm_vision
    if _llm_vision is None:
        _llm_vision = ChatAnthropic(model=MODEL_VISION, max_tokens=4096)
    return _llm_vision


@observe(name="multimodal_extract")
def multimodal_extract(state: RegWatchState) -> dict:
    trace_url = get_langfuse().get_trace_url() or ""
    doc = fitz.open(stream=document_store.get(state["doc_hash"]), filetype="pdf")
    logger.info("multimodal_extract: %s — %d pages", state["document_name"], len(doc))

    full_text_parts = []
    vision_pages = 0

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            full_text_parts.append(f"[Página {page_num + 1}]\n{text}")
            continue

        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode()

        response = _get_llm_vision().invoke([
            HumanMessage(content=[
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/png",
                        "data": img_b64,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "Extrae todo el texto de esta página de política interna. "
                        "Preserva la estructura de tablas usando formato markdown. "
                        "No omitas ningún contenido."
                    ),
                },
            ])
        ])

        page_text = f"[Página {page_num + 1} — escaneada]\n{message_text(response)}"
        full_text_parts.append(page_text)
        vision_pages += 1

    logger.info(
        "multimodal_extract complete: %d text pages, %d vision pages",
        len(full_text_parts) - vision_pages, vision_pages,
    )
    return {
        "extracted_text": "\n\n".join(full_text_parts),
        "trace_url": trace_url,
    }
