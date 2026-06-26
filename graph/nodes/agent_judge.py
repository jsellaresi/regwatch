import json
import logging

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langfuse import observe
from graph.state import RegWatchState
from graph.schemas import JudgeScores

logger = logging.getLogger(__name__)

llm_judge = ChatOpenAI(model="gpt-4o", temperature=0).with_structured_output(JudgeScores)

JUDGE_SYSTEM = """Eres un auditor experto en regulación financiera europea.
Evalúa la calidad de un informe de compliance generado por IA en tres dimensiones (0-10):
1. legal_accuracy: ¿las referencias regulatorias son correctas y bien aplicadas?
2. citation_quality: ¿las citas tienen formato correcto y son verificables?
3. actionability: ¿las remediaciones son concretas y realizables?
overall_score = promedio. approved = true si overall_score >= 7.0."""

MAX_JUDGE_ATTEMPTS = 3


@observe(name="agent_judge")
def agent_judge(state: RegWatchState) -> dict:
    attempt = state.get("judge_attempt", 0) + 1
    prompt = ChatPromptTemplate.from_messages([
        ("system", JUDGE_SYSTEM),
        ("human",
         "## Informe a evaluar\n```json\n{report}\n```\n\n"
         "## Documento original (extracto)\n{document}\n\nEvalúa el informe."),
    ])
    scores: JudgeScores = (prompt | llm_judge).invoke({
        "report": json.dumps(state["gap_report"], ensure_ascii=False),
        "document": state["extracted_text"][:2000],
    })
    logger.info(
        "agent_judge: attempt=%d overall=%.1f approved=%s (legal=%d citation=%d action=%d)",
        attempt, scores.overall_score, scores.approved,
        scores.legal_accuracy, scores.citation_quality, scores.actionability,
    )
    return {
        "judge_scores": scores.model_dump(),
        "judge_attempt": attempt,
        "judge_passed": scores.approved,
    }


def route_after_judge(state: RegWatchState) -> str:
    if state["judge_passed"]:
        return "format_report"
    if state["judge_attempt"] >= MAX_JUDGE_ATTEMPTS:
        return "human_review_checkpoint"
    return "analyze_compliance"
