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
