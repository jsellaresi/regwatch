from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate
from langfuse.decorators import observe
from graph.state import RegWatchState
from graph.schemas import GapReport
from config import langfuse

llm_analyzer = ChatAnthropic(model="claude-sonnet-4-6", temperature=0.1)
analyzer = llm_analyzer.with_structured_output(GapReport)


def _get_versioned_prompt() -> tuple[str, str]:
    prompt_obj = langfuse.get_prompt("compliance-analyzer", label="production")
    return prompt_obj.prompt, str(prompt_obj.version)


@observe(name="analyze_compliance")
def analyze_compliance(state: RegWatchState) -> dict:
    try:
        system_prompt, prompt_version = _get_versioned_prompt()
        reg_context = "\n\n".join(f"[{r['regulation']}]\n{r['content']}"
                                  for r in state["retrieved_regulations"])
        tool_context = "\n".join(t.get("result", "") for t in state.get("tool_results", []))

        prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            ("human",
             "## Documento a analizar\n{document}\n\n"
             "## Regulaciones relevantes recuperadas\n{regulations}\n\n"
             "## Información adicional de herramientas\n{tools}\n\n"
             "Genera el informe de compliance."),
        ])
        report: GapReport = (prompt | analyzer).invoke({
            "document": state["extracted_text"][:6000],
            "regulations": reg_context[:4000],
            "tools": tool_context[:1000],
        })
        return {"gap_report": report.model_dump(), "prompt_version": prompt_version, "error": ""}
    except Exception as e:
        return {"error": f"analyze_compliance: {e}"}
