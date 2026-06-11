from langchain_core.messages import AIMessage
from app.pipelines.pipeline_a.state import PipelineAState

async def analyze_phishing_risk_node(state: PipelineAState) -> dict:
    """
    Node to analyze whether the user input contains signs of voice phishing.
    """
    messages = state.get("messages", [])
    if not messages:
        return {"risk_score": 0.0, "risk_level": "LOW"}
        
    last_user_message = messages[-1].content.lower()
    
    # Basic rule-based analysis for demo (Developer A can swap this with an LLM chain)
    keywords = ["bank", "money", "card", "password", "transfer", "계좌", "송금", "비밀번호", "검찰", "경찰"]
    match_count = sum(1 for kw in keywords if kw in last_user_message)
    
    risk_score = min(match_count * 0.25, 1.0)
    risk_level = "LOW"
    if risk_score > 0.7:
        risk_level = "HIGH"
    elif risk_score > 0.3:
        risk_level = "MEDIUM"
        
    return {
        "risk_score": risk_score,
        "risk_level": risk_level
    }

async def generate_response_node(state: PipelineAState) -> dict:
    """
    Node to generate a response warning the user or guiding them based on risk score.
    """
    risk_level = state.get("risk_level", "LOW")
    risk_score = state.get("risk_score", 0.0)
    
    if risk_level == "HIGH":
        response_text = f"[경고] 보이스피싱 위험이 매우 높습니다 (위험도: {risk_score * 100:.0f}%). 통화를 즉시 종료하고 금융감독원(1332)에 신고하세요."
    elif risk_level == "MEDIUM":
        response_text = f"[주의] 의심스러운 정황이 감지되었습니다 (위험도: {risk_score * 100:.0f}%). 상대방이 금전을 요구하거나 개인정보를 물어보는지 확인하세요."
    else:
        response_text = "안전한 대화로 분석되었습니다. 추가 정보가 필요하면 언제든 입력해 주세요."
        
    return {
        "messages": [AIMessage(content=response_text)]
    }
