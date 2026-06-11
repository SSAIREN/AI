from langgraph.graph import StateGraph, END
from app.pipelines.pipeline_b.state import PipelineBState
from app.pipelines.pipeline_b.nodes import detect_scam_type_node, generate_pipeline_b_response_node

# Create the graph builder
builder = StateGraph(PipelineBState)

# Add nodes to the graph
builder.add_node("detect_scam", detect_scam_type_node)
builder.add_node("generate_response", generate_pipeline_b_response_node)

# Define transitions (edges)
builder.set_entry_point("detect_scam")
builder.add_edge("detect_scam", "generate_response")
builder.add_edge("generate_response", END)

# Compile the workflow
app = builder.compile()
