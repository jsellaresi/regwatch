import logging

from langchain_anthropic import ChatAnthropic
from config import MODEL_ANALYZER, REG_CONTEXT_CHARS
from langchain_core.messages import SystemMessage, HumanMessage
from langfuse import observe
from graph.state import RegWatchState
from graph.schemas import GapReport
from config import get_langfuse

logger = logging.getLogger(__name__)

_analyzer = None


def _get_analyzer():
    global _analyzer
    if _analyzer is None:
        _analyzer = ChatAnthropic(model=MODEL_ANALYZER, temperature=0.1).with_structured_output(GapReport)
    return _analyzer


def _get_versioned_prompt() -> tuple[str, str]:
    prompt_obj = get_langfuse().get_prompt("compliance-analyzer", label="production")
    return prompt_obj.prompt, str(prompt_obj.version)


def build_retry_feedback(state: RegWatchState) -> str:
    """Render the previous attempt's guardrail/judge feedback as a prompt
    block, or "" if this is a fresh (non-retry) run. Without this, a retry
    resends the exact same prompt — with the global LLM cache enabled
    (config.init_llm_cache) and temperature=0.1, that's a cache hit on the
    same failing response, so the retry loop can never actually correct
    anything. Pure/side-effect-free so it can be unit tested directly."""
    lines = []
    guardrail_reason = state.get("guardrail_reason")
    if guardrail_reason:
        lines.append(f"- Guardrail de salida: {guardrail_reason}")
    critical_issues = (state.get("judge_scores") or {}).get("critical_issues") or []
    lines.extend(f"- Judge: {issue}" for issue in critical_issues)
    if not lines:
        return ""
    return "## Correcciones requeridas del intento anterior\n" + "\n".join(lines) + "\n\n"


@observe(name="analyze_compliance")
def analyze_compliance(state: RegWatchState) -> dict:
    try:
        system_prompt, prompt_version = _get_versioned_prompt()
        logger.info("analyze_compliance: prompt_version=%s", prompt_version)
        reg_context = "\n\n".join(f"[{r['regulation']}]\n{r['content']}"
                                  for r in state["retrieved_regulations"])
        tool_context = "\n".join(t.get("result", "") for t in state.get("tool_results", []))
        retry_feedback = build_retry_feedback(state)
        if retry_feedback:
            logger.info("analyze_compliance: retrying with feedback from previous attempt")

        msgs = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=(
                f"{retry_feedback}"
                f"## Documento a analizar\n{state['extracted_text'][:6000]}\n\n"
                f"## Regulaciones relevantes recuperadas\n{reg_context[:REG_CONTEXT_CHARS]}\n\n"
                f"## Información adicional de herramientas\n{tool_context[:1000]}\n\n"
                "Genera el informe de compliance."
            )),
        ]
        report: GapReport = _get_analyzer().invoke(msgs)
        logger.info("analyze_compliance: %d gaps identified", len(report.gaps))
        return {"gap_report": report.model_dump(), "prompt_version": prompt_version, "error": ""}
    except Exception as e:
        logger.error("analyze_compliance error: %s", type(e).__name__, exc_info=True)
        return {"error": f"analyze_compliance: {e}"}
