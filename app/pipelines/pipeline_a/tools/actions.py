from typing import Any, Dict, List

from app.pipelines.pipeline_a.tools.client import get, post


async def check_family_gps(session_id: str, execute_tools: bool = False, **kwargs: Any) -> Dict[str, Any]:
    result = await post(
        "/ai/use/family/gps",
        execute_tools=execute_tools,
        body={
            "sessionId": session_id,
        },
    )
    return {"tool": "check_family_gps", "result": result}


async def send_family_sms_alert(
    session_id: str,
    detected_scenario: str,
    situation_summary: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/ai/use/notifications/family-alert",
        execute_tools=execute_tools,
        body={
            "sessionId": session_id,
            "scenario": detected_scenario,
            "situationSummary": situation_summary,
            "riskScore": kwargs.get("risk_score", 0.0),
        },
    )
    return {"tool": "send_family_sms_alert", "result": result}


async def notify_police(
    session_id: str,
    risk_score: float,
    situation_summary: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/ai/use/police/report",
        execute_tools=execute_tools,
        body={
            "sessionId": session_id,
            "riskScore": int(risk_score * 100),
            "incidentType": "VOICE_PHISHING",
            "summary": situation_summary,
        },
    )
    return {"tool": "notify_police", "result": result}


async def save_evidence(
    session_id: str,
    conversation_text: str,
    risk_score: float,
    detected_scenario: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/ai/use/evidence",
        execute_tools=execute_tools,
        body={
            "sessionId": session_id,
            "conversationText": conversation_text,
            "riskScore": risk_score,
            "scenario": detected_scenario,
        },
    )
    return {"tool": "save_evidence", "result": result}


async def verify_official_institution(
    session_id: str,
    detected_keywords: List[str],
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    claimed = next((keyword for keyword in detected_keywords if keyword), "unknown")
    result = await get("/institutions/verify", execute_tools=execute_tools, params={"name": claimed})
    return {"tool": "verify_official_institution", "claimed_institution": claimed, "result": result}


async def show_warning_banner(
    session_id: str,
    detected_scenario: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/ai/use/notifications/warning-banner",
        execute_tools=execute_tools,
        body={
            "sessionId": session_id,
            "scenario": detected_scenario,
            "riskScore": kwargs.get("risk_score", 0.0),
            "situationSummary": kwargs.get("situation_summary", ""),
            "message": "보이스피싱 의심 통화입니다. 통화를 중단하세요.",
        },
    )
    return {"tool": "show_warning_banner", "result": result}


async def verify_family_location(
    session_id: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await get(f"/sessions/{session_id}/family-contacts", execute_tools=execute_tools)
    return {"tool": "verify_family_location", "result": result}


async def show_transfer_warning(session_id: str, execute_tools: bool = False, **kwargs: Any) -> Dict[str, Any]:
    result = await post(
        "/notifications/fcm",
        execute_tools=execute_tools,
        body={
            "sessionId": session_id,
            "payload": {
                "type": "TRANSFER_BLOCK_WARNING",
                "message": "보이스피싱 의심 송금입니다. 이체를 중단하고 공식 연락처로 확인하세요.",
            },
        },
    )
    return {"tool": "show_transfer_warning", "block_shown": True, "result": result}


async def verify_suspicious_account(
    user_id: str,
    call_id: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    # 통화 내용 등에서 파싱된 계좌 번호 또는 기본값 사용
    account_number = kwargs.get("account_number", "unknown-account")
    bank_name = kwargs.get("bank_name", "unknown-bank")
    result = await post(
        "/ai/use/verify/account",
        execute_tools=execute_tools,
        body={
            "callId": call_id,
            "userId": user_id,
            "accountNumber": account_number,
            "bankName": bank_name,
        },
    )
    return {"tool": "verify_suspicious_account", "result": result}


async def check_spam_phone_number(
    user_id: str,
    call_id: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    phone_number = kwargs.get("phone_number", "unknown-phone")
    result = await post(
        "/ai/use/verify/phone",
        execute_tools=execute_tools,
        body={
            "callId": call_id,
            "userId": user_id,
            "phoneNumber": phone_number,
        },
    )
    return {"tool": "check_spam_phone_number", "result": result}


async def send_emergency_email_alert(
    user_id: str,
    call_id: str,
    situation_summary: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/ai/use/notifications/emergency-email",
        execute_tools=execute_tools,
        body={
            "callId": call_id,
            "userId": user_id,
            "summary": situation_summary,
            "riskScore": kwargs.get("risk_score", 0.0),
        },
    )
    return {"tool": "send_emergency_email_alert", "result": result}


async def generate_safety_guideline(
    user_id: str,
    call_id: str,
    detected_scenario: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    # 시나리오 유형에 특화된 안전 대처 요령 가이드라인 생성
    guideline = "피싱이 의심되는 통화입니다. 즉시 전화를 끊으신 후 112나 해당 공식 대고객 센터로 직접 문의하시기 바랍니다."
    if detected_scenario == "LOAN_FRAUD":
        guideline = "대환대출수수료 또는 보증금 선입금 요구는 100% 사기입니다. 진행 중인 모든 대출 절차를 즉시 중단하십시오."
    elif detected_scenario == "MESSENGER_PHISHING":
        guideline = "가족/지인의 급박한 문화상품권 대리 구매 또는 신분증 사진 전송 요구입니다. 반드시 본인과 직접 유선 통화하여 확인하십시오."
    elif detected_scenario == "DELIVERY_PHISHING":
        guideline = "택배 불명 또는 부고 링크 등을 통한 악성 앱(APK) 유도입니다. 다운로드한 파일을 절대 실행하지 마시고 출처 불명의 링크는 접속을 삼가십시오."
        
    result = await post(
        "/ai/use/notifications/guideline",
        execute_tools=execute_tools,
        body={
            "callId": call_id,
            "userId": user_id,
            "scenario": detected_scenario,
            "guideline": guideline,
        },
    )
    return {"tool": "generate_safety_guideline", "guideline": guideline, "result": result}

