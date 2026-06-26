import logging

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse import observe
from graph.state import RegWatchState
from graph.schemas import GapReport
from config import langfuse

logger = logging.getLogger(__name__)

llm_analyzer = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.1)
analyzer = llm_analyzer.with_structured_output(GapReport)


def _get_versioned_prompt() -> tuple[str, str]:
    prompt_obj = langfuse.get_prompt("compliance-analyzer", label="production")
    return prompt_obj.prompt, str(prompt_obj.version)


@observe(name="analyze_compliance")
def analyze_compliance(state: RegWatchState) -> dict:
    try:
        system_prompt, prompt_version = _get_versioned_prompt()
        logger.info("analyze_compliance: prompt_version=%s", prompt_version)
        reg_context = "\n\n".join(f"[{r['regulation']}]\n{r['content']}"
                                  for r in state["retrieved_regulations"])
        tool_context = "\n".join(t.get("result", "") for t in state.get("tool_results", []))

        msgs = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"## Documento a analizar\n{state['extracted_text'][:6000]}\n\n"
                f"## Regulaciones relevantes recuperadas\n{reg_context[:4000]}\n\n"
                f"## Información adicional de herramientas\n{tool_context[:1000]}\n\n"
                "Genera el informe de compliance."
            )),
        ]
        report: GapReport = analyzer.invoke(msgs)
        logger.info("analyze_compliance: %d gaps identified", len(report.gaps))
        return {"gap_report": report.model_dump(), "prompt_version": prompt_version, "error": ""}
    except Exception as e:
        logger.error("analyze_compliance error: %s", type(e).__name__, exc_info=True)
        return {"error": f"analyze_compliance: {e}"}
