import pytest

from graph.builder import create_error_end
from graph.nodes.human_review import route_after_human


@pytest.mark.parametrize(
    "state, expected",
    [
        ({"human_decision": "approve"}, "format_report"),
        ({"human_decision": "approve", "error": ""}, "format_report"),
        ({"human_decision": "approve", "error": "analyze_compliance: boom"}, "error_end"),
        ({"human_decision": "reject"}, "analyze_compliance"),
        ({"human_decision": "reject", "error": "analyze_compliance: boom"}, "analyze_compliance"),
    ],
)
def test_route_after_human(state, expected):
    assert route_after_human(state) == expected


def test_error_end_builds_error_report_without_gaps():
    out = create_error_end({"error": "analyze_compliance: boom"})
    assert out == {"final_report": {"error": "analyze_compliance: boom", "status": "error"}}


def test_graph_compiles_with_error_end_wired_to_end():
    from langgraph.checkpoint.memory import MemorySaver

    from graph.builder import create_regwatch_graph

    graph = create_regwatch_graph(MemorySaver()).get_graph()
    assert "error_end" in graph.nodes
    assert any(e.source == "error_end" and e.target == "__end__" for e in graph.edges)
