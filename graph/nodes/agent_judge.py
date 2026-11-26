import json
import logging

from langchain_openai import ChatOpenAI
from config import MODEL_JUDGE, REG_CONTEXT_CHARS
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe
from graph.state import RegWatchState
from graph.schemas import JudgeSubScores
from observability.tracing import log_judge_scores

logger = logging.getLogger(__name__)

_llm_judge = None


def _get_llm_judge():
    global _llm_judge
    if _llm_judge is None:
        _llm_judge = ChatOpenAI(model=MODEL_JUDGE, temperature=0).with_structured_output(JudgeSubScores)
    return _llm_judge

JUDGE_SYSTEM = """Eres un auditor experto en regulación financiera europea.
Evalúa la calidad de un informe de compliance generado por IA en tres dimensiones (0-10), usando el
texto de las regulaciones recuperadas (proporcionado abajo) como fuente de verdad:
1. legal_accuracy: ¿las referencias regulatorias son correctas y bien aplicadas?
2. citation_quality: ¿las citas son verificables contra el texto de las regulaciones proporcionado?
   No las evalúes desde tu memoria — compáralas contra el texto recuperado.
3. actionability: ¿las remediaciones son concretas y realizables?
No calcules un score global ni una decisión de aprobación: eso se calcula fuera de tu respuesta."""

JUDGE_APPROVAL_THRESHOLD = 7.0
MAX_JUDGE_ATTEMPTS = 3


def compute_judge_verdict(
    legal_accuracy: int, citation_quality: int, actionability: int,
    threshold: float = JUDGE_APPROVAL_THRESHOLD,
) -> tuple[float, bool]:
    """Average the three sub-scores and decide approval. The original prompt
    asked the LLM to do this itself ("overall_score = promedio, approved si
    >= 7.0") — three divisions and a comparison, deterministic arithmetic
    that shouldn't depend on a model doing it correctly."""
    overall_score = (legal_accuracy + citation_quality + actionability) / 3
    return overall_score, overall_score >= threshold


@observe(name="agent_judge")
def agent_judge(state: RegWatchState) -> dict:
    attempt = state.get("judge_attempt", 0) + 1
    reg_context = "\n\n".join(
        f"[{r['regulation']}]\n{r['content']}" for r in state.get("retrieved_regulations", [])
    )
    prompt = ChatPromptTemplate.from_messages([
        ("system", JUDGE_SYSTEM),
        ("human",
         "## Informe a evaluar\n```json\n{report}\n```\n\n"
         "## Regulaciones relevantes recuperadas\n{regulations}\n\n"
         "## Documento original (extracto)\n{document}\n\nEvalúa el informe."),
    ])
    sub_scores: JudgeSubScores = (prompt | _get_llm_judge()).invoke({
        "report": json.dumps(state["gap_report"], ensure_ascii=False),
        "regulations": reg_context[:REG_CONTEXT_CHARS],
        "document": state["extracted_text"][:2000],
    })
    overall_score, approved = compute_judge_verdict(
        sub_scores.legal_accuracy, sub_scores.citation_quality, sub_scores.actionability,
    )
    logger.info(
        "agent_judge: attempt=%d overall=%.1f approved=%s (legal=%d citation=%d action=%d)",
        attempt, overall_score, approved,
        sub_scores.legal_accuracy, sub_scores.citation_quality, sub_scores.actionability,
    )
    result = {
        "judge_scores": {
            **sub_scores.model_dump(),
            "overall_score": overall_score,
            "approved": approved,
        },
        "judge_attempt": attempt,
        "judge_passed": approved,
    }
    log_judge_scores(result)
    return result


def route_after_judge(state: RegWatchState) -> str:
    if state["judge_passed"]:
        return "human_review_checkpoint"
    if state["judge_attempt"] >= MAX_JUDGE_ATTEMPTS:
        return "human_review_checkpoint"
    return "analyze_compliance"
