from typing import TypedDict, Annotated, Sequence, List
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PipelineBState(TypedDict):
    """
    State definition for Pipeline B (Developer B's workspace).
    """
    # LangGraph's standard messages list with append behavior
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Custom fields for Pipeline B's specific voice phishing analysis
    detected_scam_types: List[str]  # e.g., ["IMPERSONATION", "LOAN_SCAM"]
    urgency_level: str  # e.g., "LOW", "MEDIUM", "HIGH"
