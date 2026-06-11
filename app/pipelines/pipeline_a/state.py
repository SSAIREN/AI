from typing import TypedDict, Annotated, Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class PipelineAState(TypedDict):
    """
    State definition for Pipeline A (Developer A's workspace).
    """
    # LangGraph's standard messages list with append behavior
    messages: Annotated[Sequence[BaseMessage], add_messages]
    
    # Custom fields for voice phishing detection scenario
    risk_score: float
    risk_level: str  # e.g., "LOW", "MEDIUM", "HIGH"
