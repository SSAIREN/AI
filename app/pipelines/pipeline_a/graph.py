from langgraph.graph import StateGraph, END
from app.pipelines.pipeline_a.state import PipelineAState
from app.pipelines.pipeline_a.nodes import analyze_phishing_risk_node, generate_response_node

# Create the graph builder
builder = StateGraph(PipelineAState)

# Add nodes to the graph
builder.add_node("analyze_risk", analyze_phishing_risk_node)
builder.add_node("generate_response", generate_response_node)

# Define transitions (edges)
builder.set_entry_point("analyze_risk")
builder.add_edge("analyze_risk", "generate_response")
builder.add_edge("generate_response", END)

# Compile the workflow
app = builder.compile()
