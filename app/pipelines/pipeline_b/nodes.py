from langchain_core.messages import AIMessage
from app.pipelines.pipeline_b.state import PipelineBState

async def detect_scam_type_node(state: PipelineBState) -> dict:
    """
    Node to detect the scam type (e.g., impersonating authorities or loan scams).
    """
    messages = state.get("messages", [])
    if not messages:
        return {"detected_scam_types": [], "urgency_level": "LOW"}
        
    last_user_message = messages[-1].content.lower()
    
    scam_types = []
    urgency_level = "LOW"
    
    # Basic rule-based analysis (Developer B can swap this with an LLM chain)
    if any(kw in last_user_message for kw in ["검찰", "경찰", "우체국", "법원", "police", "court"]):
        scam_types.append("기관사칭 (IMPERSONATION)")
        urgency_level = "HIGH"
    if any(kw in last_user_message for kw in ["대출", "지원금", "카드론", "신용", "loan"]):
        scam_types.append("대출빙자 (LOAN_SCAM)")
        if urgency_level != "HIGH":
            urgency_level = "MEDIUM"
            
    return {
        "detected_scam_types": scam_types,
        "urgency_level": urgency_level
    }

async def generate_pipeline_b_response_node(state: PipelineBState) -> dict:
    """
    Node to generate a response warning the user or guiding them based on scam detection.
    """
    scam_types = state.get("detected_scam_types", [])
    urgency_level = state.get("urgency_level", "LOW")
    
    if urgency_level == "HIGH":
        scam_str = ", ".join(scam_types)
        response_text = f"[경보 - {scam_str}] 공공기관을 사칭하는 사기 전화일 확률이 매우 높습니다! 전화를 끊고 해당 기관 공식 번호로 사실 여부를 확인하십시오."
    elif urgency_level == "MEDIUM":
        scam_str = ", ".join(scam_types)
        response_text = f"[주의 - {scam_str}] 불법 대출이나 허위 카드론 유도 정황이 의심됩니다. 절대 금융정보를 넘기지 마세요."
    else:
        response_text = "이상 징후가 발견되지 않은 정상 대화 내용입니다."
        
    return {
        "messages": [AIMessage(content=response_text)]
    }
