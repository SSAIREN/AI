import logging
from typing import Any, Dict, List

from langchain_core.messages import HumanMessage, SystemMessage

from app.pipelines.pipeline_a.llm import invoke_json
from app.pipelines.pipeline_a.scenarios import DETAIL_SCORE_KEYS, SCENARIOS
from app.pipelines.pipeline_a.state import PipelineAState
from app.pipelines.pipeline_a.tools import TOOL_REGISTRY
from app.pipelines.pipeline_a.demo_prompts import DETECTOR_DEMO_SYSTEM, ANALYZER_DEMO_SYSTEM
from app.pipelines.pipeline_a.nodes import _conversation_text, _risk_level

logger = logging.getLogger(__name__)


async def demo_situation_detector(state: PipelineAState) -> PipelineAState:
    text = _conversation_text(state)

    prompt = f"""
Conversation:
{text}
"""
    system_msg = DETECTOR_DEMO_SYSTEM
    fallback_result = {
        "detected_scenario": "UNKNOWN",
        "scenario_confidence": 0.0,
        "detected_keywords": [],
        "situation_summary": "보이스피싱 단서가 부족합니다.",
    }

    result = await invoke_json(
        [SystemMessage(content=system_msg), HumanMessage(content=prompt)],
        max_tokens=512,
    )

    if not isinstance(result, dict) or result.get("detected_scenario") not in {"KIDNAP_THREAT", "UNKNOWN"}:
        result = fallback_result

    logger.info(
        "[pipeline_a.detector] call_id=%s scenario=%s confidence=%.3f keywords=%s demo_mode=True",
        state.get("call_id"),
        result.get("detected_scenario", "UNKNOWN"),
        float(result.get("scenario_confidence", 0.0)),
        result.get("detected_keywords", []),
    )

    return {
        **state,
        "conversation_text": text,
        "detected_scenario": result.get("detected_scenario", "UNKNOWN"),
        "scenario_confidence": float(result.get("scenario_confidence", 0.0)),
        "detected_keywords": list(result.get("detected_keywords", [])),
        "situation_summary": str(result.get("situation_summary", "분류 결과 없음")),
        "error": None,
    }


async def demo_scenario_analyzer(state: PipelineAState) -> PipelineAState:
    scenario = str(state.get("detected_scenario", "UNKNOWN"))
    scenario_cfg = SCENARIOS.get(scenario)
    recommended_tools = scenario_cfg.required_tools + scenario_cfg.optional_tools if scenario_cfg else []

    prompt = f"""
Scenario: {scenario}
Scenario name: {scenario_cfg.name_kr if scenario_cfg else "unknown"}
Confidence: {float(state.get("scenario_confidence", 0.0)):.2f}
Detected keywords: {", ".join(state.get("detected_keywords", []))}
Situation summary: {state.get("situation_summary", "")}
Recommended tools: {recommended_tools}

Conversation:
{state.get("conversation_text", "")}
"""
    system_msg = ANALYZER_DEMO_SYSTEM

    result = await invoke_json(
        [SystemMessage(content=system_msg), HumanMessage(content=prompt)],
        max_tokens=800,
    )

    if not isinstance(result, dict):
        result = {
            "risk_score": 0.0,
            "scenario_detail_scores": {key: 0.0 for key in DETAIL_SCORE_KEYS},
            "tool_call_reasons": [],
            "tools_to_call": [],
        }

    llm_score = float(result.get("risk_score", 0.0))
    blended_score = round(min(max(llm_score, 0.0), 1.0), 3)
    tools_to_call = [tool for tool in result.get("tools_to_call", []) if tool in TOOL_REGISTRY and tool in recommended_tools]

    detail_scores = result.get("scenario_detail_scores", {})
    detail_scores = {key: float(detail_scores.get(key, 0.0)) for key in DETAIL_SCORE_KEYS}

    logger.info(
        "[pipeline_a.analyzer] call_id=%s scenario=%s risk_level=%s risk_score=%.3f tools=%s demo_mode=True",
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
        "scenario_detail_scores": detail_scores,
        "tool_call_reasons": list(result.get("tool_call_reasons", [])),
        "tools_to_call": tools_to_call,
        "error": None,
    }
