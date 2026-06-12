from langgraph.graph import END, StateGraph

from app.pipelines.pipeline_a.nodes import (
    generate_response_node,
    observe_only,
    response_builder,
    route_by_risk,
    scenario_analyzer,
    situation_detector,
    tool_executor,
)
from app.pipelines.pipeline_a.state import PipelineAState


builder = StateGraph(PipelineAState)

builder.add_node("situation_detector", situation_detector)
builder.add_node("scenario_analyzer", scenario_analyzer)
builder.add_node("tool_executor", tool_executor)
builder.add_node("observe_only", observe_only)
builder.add_node("response_builder", response_builder)
builder.add_node("generate_response", generate_response_node)

builder.set_entry_point("situation_detector")
builder.add_edge("situation_detector", "scenario_analyzer")
builder.add_conditional_edges(
    "scenario_analyzer",
    route_by_risk,
    {
        "respond": "response_builder",
        "observe": "observe_only",
        "execute": "tool_executor",
    },
)
builder.add_edge("tool_executor", "generate_response")
builder.add_edge("observe_only", "generate_response")
builder.add_edge("response_builder", "generate_response")
builder.add_edge("generate_response", END)

app = builder.compile()
