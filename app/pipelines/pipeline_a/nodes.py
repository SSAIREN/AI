import asyncio
import logging
from typing import Any, Dict, List

from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.pipelines.pipeline_a.llm import invoke_json
from app.pipelines.pipeline_a.scenarios import DETAIL_SCORE_KEYS, SCENARIOS
from app.pipelines.pipeline_a.state import PipelineAState
from app.pipelines.pipeline_a.tools import TOOL_REGISTRY

logger = logging.getLogger(__name__)

from app.pipelines.pipeline_a.prompts import DETECTOR_SYSTEM, ANALYZER_SYSTEM, UNIFIED_SYSTEM


def _conversation_text(state: PipelineAState) -> str:
    if state.get("conversation_text"):
        return str(state["conversation_text"])

    messages = state.get("messages", [])
    return "\n".join(str(getattr(message, "content", message)) for message in messages)


def _keyword_detector(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    matches: list[tuple[str, list[str]]] = []

    for scenario_id, config in SCENARIOS.items():
        found = [keyword for keyword in config.keywords if keyword.lower() in lowered]
        if found:
            matches.append((scenario_id, found))

    if not matches:
        return {
            "detected_scenario": "UNKNOWN",
            "scenario_confidence": 0.0,
            "detected_keywords": [],
            "situation_summary": "보이스피싱 단서가 부족합니다.",
        }

    scenario_id, keywords = max(matches, key=lambda item: len(item[1]))
    confidence = min(0.45 + len(keywords) * 0.15, 0.95)
    return {
        "detected_scenario": scenario_id,
        "scenario_confidence": round(confidence, 2),
        "detected_keywords": keywords,
        "situation_summary": f"{SCENARIOS[scenario_id].name_kr} 의심 정황",
    }


def _risk_level(score: float) -> str:
    if score < 0.40:
        return "ABSTAIN"
    if score < 0.55:
        return "LOW"
    if score < 0.75:
        return "MEDIUM"
    return "HIGH"


def _fallback_analysis(state: PipelineAState) -> Dict[str, Any]:
    text = _conversation_text(state).lower()
    scenario = str(state.get("detected_scenario", "UNKNOWN"))
    scenario_cfg = SCENARIOS.get(scenario)
    keywords = state.get("detected_keywords", [])

    urgency = _has_any(text, ["지금", "즉시", "바로", "빨리", "시간 없다", "끊지 마"])
    finance = _has_any(text, ["돈", "입금", "송금", "이체", "계좌", "카드", "otp", "인증번호"])
    isolation = _has_any(text, ["경찰 부르지", "말하지 마", "비밀", "혼자", "통화 끊지"])
    identity = scenario in {"INSTITUTION_IMPERSONATION", "FAMILY_IMPERSONATION"} or _has_any(
        text, ["검찰", "경찰", "금융감독원", "엄마", "아빠", "아들", "딸"]
    )
    pattern = bool(keywords) or scenario != "UNKNOWN"

    detail_scores = {
        "urgency_pressure": 0.8 if urgency else 0.2,
        "financial_demand": 0.85 if finance else 0.15,
        "isolation_attempt": 0.8 if isolation else 0.1,
        "identity_deception": 0.75 if identity else 0.1,
        "behavioral_pattern": 0.75 if pattern else 0.1,
    }
    base_score = sum(detail_scores.values()) / len(detail_scores)
    weighted_score = base_score * (scenario_cfg.risk_weight if scenario_cfg else 0.7)

    recommended_tools = []
    if scenario_cfg:
        recommended_tools = scenario_cfg.required_tools
        if weighted_score >= 0.75:
            recommended_tools = scenario_cfg.required_tools + scenario_cfg.optional_tools

    return {
        "risk_score": round(min(max(weighted_score, 0.0), 1.0), 3),
        "scenario_detail_scores": detail_scores,
        "tool_call_reasons": [
            {
                "tool": tool,
                "reason": f"{scenario_cfg.name_kr if scenario_cfg else 'UNKNOWN'} 대응을 위해 필요",
                "priority": "IMMEDIATE" if tool in {"show_transfer_warning", "check_family_gps"} else "BACKGROUND",
            }
            for tool in recommended_tools
        ],
        "tools_to_call": recommended_tools,
    }


def _has_any(text: str, keywords: List[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)


def _run_rule_based_fallback(text: str) -> Dict[str, Any]:
    lowered = text.lower()
    detected_scenario = "UNKNOWN"
    detected_keywords = []

    for scenario_id, config in SCENARIOS.items():
        found = [kw for kw in config.keywords if kw.lower() in lowered]
        if found:
            if len(found) > len(detected_keywords):
                detected_scenario = scenario_id
                detected_keywords = found

    if detected_scenario == "UNKNOWN":
        return {
            "detected_scenario": "UNKNOWN",
            "scenario_confidence": 0.0,
            "detected_keywords": [],
            "situation_summary": "보이스피싱 단서가 부족합니다.",
            "risk_score": 0.0,
            "scenario_detail_scores": {key: 0.0 for key in DETAIL_SCORE_KEYS},
            "tool_call_reasons": [],
            "tools_to_call": [],
        }

    cfg = SCENARIOS[detected_scenario]
    confidence = min(0.5 + len(detected_keywords) * 0.1, 0.95)

    urgency = _has_any(lowered, ["지금", "즉시", "바로", "빨리", "시간 없다", "끊지 마"])
    finance = _has_any(lowered, ["돈", "입금", "송금", "이체", "계좌", "카드", "otp", "인증번호"])
    isolation = _has_any(lowered, ["경찰 부르지", "말하지 마", "비밀", "혼자", "통화 끊지"])
    identity = detected_scenario in {"INSTITUTION_IMPERSONATION", "FAMILY_IMPERSONATION"} or _has_any(
        lowered, ["검찰", "경찰", "금융감독원", "엄마", "아빠", "아들", "딸"]
    )

    detail_scores = {
        "urgency_pressure": 0.85 if urgency else 0.2,
        "financial_demand": 0.9 if finance else 0.15,
        "isolation_attempt": 0.8 if isolation else 0.1,
        "identity_deception": 0.8 if identity else 0.1,
        "behavioral_pattern": 0.75,
    }

    base_score = sum(detail_scores.values()) / len(detail_scores)
    risk_score = round(base_score * cfg.risk_weight, 3)

    tools = cfg.required_tools
    if risk_score >= 0.75:
        tools = list(set(cfg.required_tools + cfg.optional_tools))

    tool_call_reasons = [
        {
            "tool": tool,
            "reason": f"룰베이스 매칭: {cfg.name_kr} 긴급 대응",
            "priority": "IMMEDIATE" if tool in {"show_transfer_warning", "check_family_gps", "verify_suspicious_account"} else "BACKGROUND",
        }
        for tool in tools
    ]

    return {
        "detected_scenario": detected_scenario,
        "scenario_confidence": round(confidence, 2),
        "detected_keywords": detected_keywords,
        "situation_summary": f"룰베이스 분석: {cfg.name_kr} 의심 정황",
        "risk_score": risk_score,
        "scenario_detail_scores": detail_scores,
        "tool_call_reasons": tool_call_reasons,
        "tools_to_call": tools,
    }


def _validate_and_sanitize_result(result: Any, text: str) -> Dict[str, Any]:
    if not isinstance(result, dict):
        return _run_rule_based_fallback(text)

    sanitized = {}

    scenario = result.get("detected_scenario")
    if not scenario or (scenario not in SCENARIOS and scenario != "UNKNOWN"):
        if isinstance(scenario, str) and scenario.isupper() and len(scenario) > 2:
            sanitized["detected_scenario"] = scenario
        else:
            sanitized["detected_scenario"] = "UNKNOWN"
    else:
        sanitized["detected_scenario"] = scenario

    try:
        sanitized["scenario_confidence"] = float(result.get("scenario_confidence", 0.5))
    except (ValueError, TypeError):
        sanitized["scenario_confidence"] = 0.5

    keywords = result.get("detected_keywords")
    sanitized["detected_keywords"] = list(keywords) if isinstance(keywords, list) else []
    sanitized["situation_summary"] = str(result.get("situation_summary", "보이스피싱 분석 중"))[:40]

    try:
        sanitized["risk_score"] = min(max(float(result.get("risk_score", 0.0)), 0.0), 1.0)
    except (ValueError, TypeError):
        sanitized["risk_score"] = 0.0

    detail_scores = result.get("scenario_detail_scores")
    sanitized_details = {}
    for key in DETAIL_SCORE_KEYS:
        try:
            val = detail_scores.get(key) if isinstance(detail_scores, dict) else 0.0
            sanitized_details[key] = min(max(float(val), 0.0), 1.0)
        except (ValueError, TypeError):
            sanitized_details[key] = 0.0
    sanitized["scenario_detail_scores"] = sanitized_details

    tools_to_call = result.get("tools_to_call")
    if isinstance(tools_to_call, list):
        sanitized["tools_to_call"] = [t for t in tools_to_call if t in TOOL_REGISTRY]
    else:
        sanitized["tools_to_call"] = []

    reasons = result.get("tool_call_reasons")
    sanitized["tool_call_reasons"] = list(reasons) if isinstance(reasons, list) else []

    if sanitized["detected_scenario"] != "UNKNOWN" and not sanitized["tools_to_call"]:
        cfg = SCENARIOS.get(sanitized["detected_scenario"])
        if cfg:
            sanitized["tools_to_call"] = cfg.required_tools
            sanitized["tool_call_reasons"] = [
                {
                    "tool": t,
                    "reason": f"시나리오 매핑 복구: {cfg.name_kr} 예방 조치",
                    "priority": "IMMEDIATE" if t in {"show_transfer_warning", "check_family_gps"} else "BACKGROUND",
                }
                for t in cfg.required_tools
            ]

    return sanitized


async def _prod_situation_detector(state: PipelineAState) -> PipelineAState:
    text = _conversation_text(state)
    prompt = f"""
Pre-detected type: {state.get("pre_detected_type", "UNKNOWN")}
Pre-detected risk: {float(state.get("pre_detected_risk", 0.0)):.2f}

Conversation:
{text}
"""
    system_msg = UNIFIED_SYSTEM
    fallback_result = _run_rule_based_fallback(text)

    # 1회 호출로 모든 정보를 파싱받기 위해 unified_system 사용
    result = await invoke_json(
        [SystemMessage(content=system_msg), HumanMessage(content=prompt)],
        max_tokens=800,
    )

    # 유효성 검증 및 3단계 방어벽 작동
    sanitized = _validate_and_sanitize_result(result, text)

    logger.info(
        "[pipeline_a.detector] call_id=%s scenario=%s confidence=%.3f keywords=%s demo_mode=False (Unified)",
        state.get("call_id"),
        sanitized.get("detected_scenario", "UNKNOWN"),
        float(sanitized.get("scenario_confidence", 0.0)),
        sanitized.get("detected_keywords", []),
    )

    return {
        **state,
        "conversation_text": text,
        "detected_scenario": sanitized.get("detected_scenario", "UNKNOWN"),
        "scenario_confidence": float(sanitized.get("scenario_confidence", 0.0)),
        "detected_keywords": list(sanitized.get("detected_keywords", [])),
        "situation_summary": str(sanitized.get("situation_summary", "분류 결과 없음")),
        "risk_score": float(sanitized.get("risk_score", 0.0)),
        "scenario_detail_scores": sanitized.get("scenario_detail_scores", {}),
        "tool_call_reasons": list(sanitized.get("tool_call_reasons", [])),
        "tools_to_call": list(sanitized.get("tools_to_call", [])),
        "error": None,
    }


async def situation_detector(state: PipelineAState) -> PipelineAState:
    if state.get("demo_mode"):
        from app.pipelines.pipeline_a.demo_nodes import demo_situation_detector
        return await demo_situation_detector(state)
    return await _prod_situation_detector(state)


async def _prod_scenario_analyzer(state: PipelineAState) -> PipelineAState:
    # 이미 1단계(situation_detector)에서 모든 LLM 분석이 끝났으므로 추가 LLM 호출을 생략(Passthrough)
    # 기존 가중치 및 이전 위험도 지표를 고려한 최종 점수 계산만 진행하여 지연시간 최소화
    scenario = str(state.get("detected_scenario", "UNKNOWN"))
    scenario_cfg = SCENARIOS.get(scenario)

    llm_score = float(state.get("risk_score", 0.0))
    pre_detected_risk = float(state.get("pre_detected_risk", 0.0))
    weight = scenario_cfg.risk_weight if scenario_cfg else 1.0

    blended_score = round(min(max(llm_score, llm_score * 0.7 + pre_detected_risk * weight * 0.3), 1.0), 3)
    tools_to_call = list(state.get("tools_to_call", []))

    logger.info(
        "[pipeline_a.analyzer] call_id=%s scenario=%s risk_level=%s risk_score=%.3f tools=%s demo_mode=False (Passthrough)",
        state.get("call_id"),
        scenario,
        _risk_level(blended_score),
        blended_score,
        tools_to_call,
    )

    return {
        **state,
        "risk_score": blended_score,
        "risk_level": _risk_level(blended_score),
        "error": None,
    }


async def scenario_analyzer(state: PipelineAState) -> PipelineAState:
    if state.get("demo_mode"):
        from app.pipelines.pipeline_a.demo_nodes import demo_scenario_analyzer
        return await demo_scenario_analyzer(state)
    return await _prod_scenario_analyzer(state)


def route_by_risk(state: PipelineAState) -> str:
    scenario = state.get("detected_scenario", "UNKNOWN")
    risk_level = state.get("risk_level", "ABSTAIN")

    if scenario == "UNKNOWN" or risk_level == "ABSTAIN":
        return "respond"
    if risk_level == "LOW":
        return "observe"
    return "execute"


def _tool_kwargs(state: PipelineAState) -> Dict[str, Any]:
    return {
        "user_id": state.get("user_id", "demo-user"),
        "call_id": state.get("call_id", "unknown-call"),
        "detected_scenario": state.get("detected_scenario", "UNKNOWN"),
        "detected_keywords": state.get("detected_keywords", []),
        "situation_summary": state.get("situation_summary", ""),
        "risk_score": state.get("risk_score", 0.0),
        "conversation_text": state.get("conversation_text", ""),
        "execute_tools": bool(state.get("execute_tools", False)),
    }


async def _run_tool(tool_name: str, kwargs: Dict[str, Any]) -> Dict[str, Any]:
    fn = TOOL_REGISTRY.get(tool_name)
    if fn is None:
        logger.warning("[pipeline_a.executor] tool=%s status=NOT_FOUND", tool_name)
        return {"tool": tool_name, "status": "NOT_FOUND"}

    try:
        logger.info("[pipeline_a.executor] tool=%s started call_id=%s", tool_name, kwargs.get("call_id"))
        result = await fn(**kwargs)
        status = result.get("status") or result.get("result", {}).get("status") or "SUCCESS"
        logger.info(
            "[pipeline_a.executor] tool=%s finished call_id=%s status=%s",
            tool_name,
            kwargs.get("call_id"),
            status,
        )
        return {"status": status, **result}
    except Exception as exc:
        logger.warning("[pipeline_a.executor] tool=%s failed: %s", tool_name, exc)
        return {"tool": tool_name, "status": "ERROR", "error": str(exc)}


async def tool_executor(state: PipelineAState) -> PipelineAState:
    tools_to_call = state.get("tools_to_call", [])
    kwargs = _tool_kwargs(state)

    logger.info("[pipeline_a.executor] call_id=%s tools=%s", state.get("call_id"), tools_to_call)

    results = await asyncio.gather(*[_run_tool(tool, kwargs) for tool in tools_to_call])
    actions = [f"{result.get('status', 'UNKNOWN')} {result.get('tool', 'unknown')}" for result in results]

    return {
        **state,
        "tool_results": results,
        "final_actions_taken": actions,
        "response_summary": _build_summary(state, actions),
    }


async def observe_only(state: PipelineAState) -> PipelineAState:
    actions = ["MONITORING risk pattern logged", "NO_EXTERNAL_TOOL low risk branch"]
    return {
        **state,
        "tool_results": [],
        "final_actions_taken": actions,
        "response_summary": _build_summary(state, actions),
    }


async def response_builder(state: PipelineAState) -> PipelineAState:
    return {
        **state,
        "tool_results": state.get("tool_results", []),
        "final_actions_taken": state.get("final_actions_taken", []),
        "response_summary": _build_summary(state, state.get("final_actions_taken", [])),
    }


async def generate_response_node(state: PipelineAState) -> Dict[str, Any]:
    summary = state.get("response_summary") or _build_summary(state, state.get("final_actions_taken", []))
    return {"messages": [AIMessage(content=summary)]}


def _build_summary(state: PipelineAState, actions: List[str]) -> str:
    scenario = state.get("detected_scenario", "UNKNOWN")
    risk_level = state.get("risk_level", "ABSTAIN")
    risk_score = float(state.get("risk_score", 0.0))
    situation = state.get("situation_summary", "요약 없음")

    if risk_level == "HIGH":
        prefix = "[긴급 경고]"
        guidance = "통화를 중단하고 송금/개인정보 제공을 멈춘 뒤 공식 연락처로 확인하세요."
    elif risk_level == "MEDIUM":
        prefix = "[주의]"
        guidance = "상대방 신원과 요구 내용을 공식 채널로 재확인하세요."
    elif risk_level == "LOW":
        prefix = "[관찰]"
        guidance = "현재 위험도는 낮지만 금전/인증번호 요구가 나오면 즉시 중단하세요."
    else:
        prefix = "[판단 보류]"
        guidance = "보이스피싱으로 단정할 근거가 부족합니다. 추가 대화가 있으면 다시 분석하세요."

    action_text = ", ".join(actions) if actions else "실행한 외부 조치 없음"
    return (
        f"{prefix} 시나리오={scenario}, 위험도={risk_level}({risk_score * 100:.0f}%). "
        f"{situation} {guidance} 조치: {action_text}"
    )
