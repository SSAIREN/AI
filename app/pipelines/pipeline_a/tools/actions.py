from typing import Any, Dict, List

from app.pipelines.pipeline_a.tools.client import get, post


async def check_family_gps(user_id: str, call_id: str, execute_tools: bool = False, **kwargs: Any) -> Dict[str, Any]:
    contacts = await get(f"/users/{user_id}/family-contacts", execute_tools=execute_tools)
    if contacts.get("status") == "DRY_RUN":
        return {"tool": "check_family_gps", **contacts}

    family_contacts = contacts.get("contacts", [])
    gps_results = []
    for contact in family_contacts:
        target_id = contact.get("id")
        if not target_id:
            continue
        cached = await get("/gps/cached", execute_tools=execute_tools, params={"userId": user_id, "targetId": target_id})
        await post("/gps/request", execute_tools=execute_tools, body={"userId": user_id, "targetId": target_id})
        gps_results.append({"contact": contact, "location": cached})

    return {"tool": "check_family_gps", "family_locations": gps_results, "count": len(gps_results)}


async def send_family_sms_alert(
    user_id: str,
    call_id: str,
    detected_scenario: str,
    situation_summary: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    body = {
        "senderId": user_id,
        "targetIds": kwargs.get("guardian_ids", []),
        "payload": {
            "type": "EMERGENCY_PHISHING_ALERT",
            "callId": call_id,
            "scenario": detected_scenario,
            "title": "SSAIREN 긴급 알림",
            "body": situation_summary,
        },
    }
    result = await post("/notifications/fcm", execute_tools=execute_tools, body=body)
    return {"tool": "send_family_sms_alert", "result": result}


async def notify_police(
    user_id: str,
    call_id: str,
    risk_score: float,
    situation_summary: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/police/report",
        execute_tools=execute_tools,
        body={
            "callId": call_id,
            "userId": user_id,
            "riskScore": int(risk_score * 100),
            "incidentType": "VOICE_PHISHING",
            "summary": situation_summary,
        },
    )
    return {"tool": "notify_police", "result": result}


async def save_evidence(
    call_id: str,
    user_id: str,
    conversation_text: str,
    risk_score: float,
    detected_scenario: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        f"/incidents/{call_id}/evidence",
        execute_tools=execute_tools,
        body={
            "userId": user_id,
            "conversationText": conversation_text,
            "riskScore": risk_score,
            "scenario": detected_scenario,
            "source": "PIPELINE_A_LANGGRAPH",
        },
    )
    return {"tool": "save_evidence", "encrypted": True, "result": result}


async def verify_official_institution(
    user_id: str,
    call_id: str,
    detected_keywords: List[str],
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    claimed = next((keyword for keyword in detected_keywords if keyword), "unknown")
    result = await get("/institutions/verify", execute_tools=execute_tools, params={"name": claimed})
    return {"tool": "verify_official_institution", "claimed_institution": claimed, "result": result}


async def show_warning_banner(
    user_id: str,
    call_id: str,
    detected_scenario: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await post(
        "/notifications/fcm",
        execute_tools=execute_tools,
        body={
            "senderId": user_id,
            "targetIds": [user_id],
            "payload": {
                "type": "WARNING_BANNER",
                "callId": call_id,
                "scenario": detected_scenario,
            },
        },
    )
    return {"tool": "show_warning_banner", "result": result}


async def verify_family_location(
    user_id: str,
    call_id: str,
    execute_tools: bool = False,
    **kwargs: Any,
) -> Dict[str, Any]:
    result = await get(f"/users/{user_id}/family-contacts", execute_tools=execute_tools)
    return {"tool": "verify_family_location", "result": result}


async def show_transfer_warning(user_id: str, call_id: str, execute_tools: bool = False, **kwargs: Any) -> Dict[str, Any]:
    result = await post(
        "/notifications/fcm",
        execute_tools=execute_tools,
        body={
            "senderId": user_id,
            "targetIds": [user_id],
            "payload": {
                "type": "TRANSFER_BLOCK_WARNING",
                "callId": call_id,
                "message": "보이스피싱 의심 송금입니다. 이체를 중단하고 공식 연락처로 확인하세요.",
            },
        },
    )
    return {"tool": "show_transfer_warning", "block_shown": True, "result": result}
