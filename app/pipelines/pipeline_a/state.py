from typing import Annotated, Any, Dict, List, Literal, Sequence, TypedDict

from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages


ScenarioType = Literal[
    "KIDNAP_THREAT",
    "INSTITUTION_IMPERSONATION",
    "FAMILY_IMPERSONATION",
    "SAFE_ACCOUNT_TRANSFER",
    "UNKNOWN",
]

RiskLevel = Literal["ABSTAIN", "LOW", "MEDIUM", "HIGH"]


class PipelineAState(TypedDict, total=False):
    """State for the SSAIREN voice-phishing pipeline."""

    messages: Annotated[Sequence[BaseMessage], add_messages]

    call_id: str
    user_id: str
    conversation_text: str
    pre_detected_type: str
    pre_detected_risk: float
    execute_tools: bool

    detected_scenario: ScenarioType
    scenario_confidence: float
    detected_keywords: List[str]
    situation_summary: str

    risk_score: float
    risk_level: RiskLevel
    scenario_detail_scores: Dict[str, float]
    tool_call_reasons: List[Dict[str, str]]
    tools_to_call: List[str]

    tool_results: List[Dict[str, Any]]
    final_actions_taken: List[str]
    response_summary: str

    error: str | None
