import logging

import fitz
import base64
from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage
from langfuse import observe
from config import langfuse
from graph.state import RegWatchState

logger = logging.getLogger(__name__)

llm_vision = ChatAnthropic(model="claude-sonnet-4-6", max_tokens=4096)


@observe(name="multimodal_extract")
def multimodal_extract(state: RegWatchState) -> dict:
    trace_url = langfuse.get_trace_url() or ""
    doc = fitz.open(stream=state["document_bytes"], filetype="pdf")
    logger.info("multimodal_extract: %s — %d pages", state["document_name"], len(doc))

    full_text_parts = []
    image_descriptions = []

    for page_num, page in enumerate(doc):
        text = page.get_text()
        if text.strip():
            full_text_parts.append(f"[Página {page_num + 1}]\n{text}")
            continue

        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")
        img_b64 = base64.b64encode(img_bytes).decode()

        response = llm_vision.invoke([
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

        page_text = f"[Página {page_num + 1} — escaneada]\n{response.content}"
        full_text_parts.append(page_text)
        image_descriptions.append(img_b64)

    logger.info(
        "multimodal_extract complete: %d text pages, %d vision pages",
        len(full_text_parts) - len(image_descriptions), len(image_descriptions),
    )
    return {
        "extracted_text": "\n\n".join(full_text_parts),
        "extracted_images": image_descriptions,
        "trace_url": trace_url,
    }
