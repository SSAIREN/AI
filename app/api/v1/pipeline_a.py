import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal
from uuid import uuid4

import httpx
from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Path
from langchain_core.messages import HumanMessage
from pydantic import BaseModel, Field
from starlette import status

from app.core.config import settings
from app.pipelines.pipeline_a.graph import app as pipeline_a_graph

router = APIRouter()
logger = logging.getLogger(__name__)

JobStatus = Literal["PENDING", "RUNNING", "SUCCEEDED", "FAILED"]
_JOBS: Dict[str, Dict[str, Any]] = {}


class PipelineAInput(BaseModel):
    message: str = Field(
        description="보이스피싱 위험도를 분석할 STT 전문 또는 통화 내용입니다.",
        examples=["검찰 수사관입니다. 대포통장에 연루됐으니 지금 안전 계좌로 돈을 이체하세요."],
    )
    call_id: str | None = Field(
        default=None,
        description="요청 또는 통화 고유 ID입니다. 생략하면 서버가 UUID를 생성합니다.",
        examples=["call-20260612-0001"],
    )
    user_id: str = Field(
        default="demo-user",
        description="통화와 연결된 서비스 사용자 ID입니다.",
        examples=["user-abc123"],
    )
    pre_detected_type: str = Field(
        default="UNKNOWN",
        description="상위 시스템이나 1차 탐지기가 미리 판단한 시나리오입니다. 없으면 UNKNOWN을 사용합니다.",
        examples=["INSTITUTION_IMPERSONATION"],
    )
    pre_detected_risk: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="상위 시스템이나 1차 탐지기가 계산한 위험 점수입니다. 범위는 0.0부터 1.0까지입니다.",
        examples=[0.2],
    )
    execute_tools: bool = Field(
        default=False,
        description=(
            "false이면 외부 Spring/FCM/GPS API를 실제 호출하지 않고 DRY_RUN 결과를 반환합니다. "
            "실제 연동 설정이 완료된 경우에만 true로 사용하세요."
        ),
        examples=[False],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "검찰 수사관입니다. 대포통장에 연루됐으니 지금 안전 계좌로 돈을 이체하세요.",
                "user_id": "user-abc123",
                "pre_detected_type": "UNKNOWN",
                "pre_detected_risk": 0.2,
                "execute_tools": False,
            }
        }
    }


class PipelineADemoInput(BaseModel):
    message: str = Field(
        description="데모용 보이스피싱 위험도를 분석할 STT 전문 또는 통화 내용입니다.",
        examples=["아들을 데리고 있다, 경찰에 신고하면 죽이겠다, 당장 돈 보내라"],
    )
    call_id: str | None = Field(
        default=None,
        description="요청 또는 통화 고유 ID입니다. 생략하면 서버가 UUID를 생성합니다.",
        examples=["call-demo-20260612-0001"],
    )
    user_id: str = Field(
        default="demo-user",
        description="통화와 연결된 서비스 사용자 ID입니다.",
        examples=["user-abc123"],
    )

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "아들을 데리고 있다, 경찰에 신고하면 죽이겠다, 당장 돈 보내라",
                "user_id": "user-abc123",
            }
        }
    }


class PipelineAOutput(BaseModel):
    call_id: str = Field(description="분석 요청 또는 통화 ID입니다.", examples=["call-20260612-0001"])
    response: str = Field(description="사용자 또는 호출 시스템에 전달할 최종 요약 문구입니다.")
    risk_score: float = Field(description="최종 위험 점수입니다. 범위는 0.0부터 1.0까지입니다.", examples=[0.585])
    risk_level: str = Field(description="최종 위험 등급입니다. ABSTAIN, LOW, MEDIUM, HIGH 중 하나입니다.", examples=["MEDIUM"])
    detected_scenario: str = Field(description="탐지된 보이스피싱 시나리오 ID입니다.", examples=["INSTITUTION_IMPERSONATION"])
    scenario_confidence: float = Field(description="시나리오 분류 신뢰도입니다. 범위는 0.0부터 1.0까지입니다.", examples=[0.9])
    detected_keywords: List[str] = Field(description="입력 내용에서 감지된 위험 키워드 목록입니다.", examples=[["검찰", "대포통장"]])
    situation_summary: str = Field(description="통화 상황을 짧게 요약한 문장입니다.")
    scenario_detail_scores: Dict[str, float] = Field(description="긴급성, 금전 요구, 고립 유도 등 위험 축별 점수입니다.")
    tool_call_reasons: List[Dict[str, Any]] = Field(description="각 tool을 선택한 이유와 우선순위입니다.")
    tools_to_call: List[str] = Field(description="분석기가 실행 대상으로 선택한 tool 이름 목록입니다.")
    tool_results: List[Dict[str, Any]] = Field(description="tool 실행 결과입니다. 외부 연동이 꺼져 있으면 DRY_RUN 결과가 들어갑니다.")
    final_actions_taken: List[str] = Field(description="최종으로 수행했거나 요청한 조치 목록입니다.")
    history: List[Dict[str, Any]] = Field(description="LangGraph가 반환한 대화 이력입니다.")
    error: str | None = Field(default=None, description="파이프라인 실행 중 발생한 오류입니다. 오류가 없으면 null입니다.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "call_id": "call-20260612-0001",
                "response": "[주의] 시나리오=INSTITUTION_IMPERSONATION, 위험도=MEDIUM(58%). 기관 사칭형 의심 정황...",
                "risk_score": 0.585,
                "risk_level": "MEDIUM",
                "detected_scenario": "INSTITUTION_IMPERSONATION",
                "scenario_confidence": 0.9,
                "detected_keywords": ["검찰", "대포통장", "안전 계좌"],
                "situation_summary": "기관 사칭형 의심 정황",
                "scenario_detail_scores": {
                    "urgency_pressure": 0.8,
                    "financial_demand": 0.85,
                    "isolation_attempt": 0.1,
                    "identity_deception": 0.75,
                    "behavioral_pattern": 0.75,
                },
                "tool_call_reasons": [
                    {
                        "tool": "verify_official_institution",
                        "reason": "기관 사칭 여부 확인을 위해 공식 기관 조회가 필요합니다.",
                        "priority": "BACKGROUND",
                    }
                ],
                "tools_to_call": ["verify_official_institution", "show_warning_banner", "save_evidence"],
                "tool_results": [{"tool": "verify_official_institution", "status": "DRY_RUN"}],
                "final_actions_taken": ["DRY_RUN verify_official_institution"],
                "history": [
                    {"role": "user", "content": "검찰 수사관입니다..."},
                    {"role": "assistant", "content": "[주의] 시나리오=INSTITUTION_IMPERSONATION..."},
                ],
                "error": None,
            }
        }
    }


class PipelineAJobAccepted(BaseModel):
    call_id: str = Field(description="접수된 분석 ID입니다. 이후 상태 조회에 사용합니다.", examples=["call-20260612-0001"])
    status: JobStatus = Field(description="접수 직후 작업 상태입니다.", examples=["PENDING"])
    status_url: str = Field(description="이 작업의 상태를 조회할 상대 URL입니다.", examples=["/api/v1/pipeline-a/runs/call-20260612-0001"])


class PipelineAJobStatus(BaseModel):
    call_id: str = Field(description="분석 작업 ID입니다.", examples=["call-20260612-0001"])
    status: JobStatus = Field(description="현재 작업 상태입니다.", examples=["SUCCEEDED"])
    created_at: str = Field(description="작업이 생성된 UTC ISO 시각입니다.")
    updated_at: str = Field(description="작업 상태가 마지막으로 갱신된 UTC ISO 시각입니다.")
    tools_to_call: List[str] = Field(default_factory=list, description="현재까지 선택된 tool 이름 목록입니다.")
    final_actions_taken: List[str] = Field(default_factory=list, description="현재까지 완료됐거나 요청된 조치 목록입니다.")
    result: PipelineAOutput | None = Field(default=None, description="작업이 성공하면 최종 분석 결과가 들어갑니다.")
    error: str | None = Field(default=None, description="작업이 실패하면 실패 사유가 들어갑니다.")

    model_config = {
        "json_schema_extra": {
            "example": {
                "call_id": "call-20260612-0001",
                "status": "SUCCEEDED",
                "created_at": "2026-06-12T02:30:00+00:00",
                "updated_at": "2026-06-12T02:30:03+00:00",
                "tools_to_call": ["verify_official_institution", "show_warning_banner", "save_evidence"],
                "final_actions_taken": [
                    "DRY_RUN verify_official_institution",
                    "DRY_RUN show_warning_banner",
                    "DRY_RUN save_evidence",
                ],
                "result": None,
                "error": None,
            }
        }
    }


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _build_initial_state(payload: PipelineAInput, call_id: str, demo_mode: bool = False) -> Dict[str, Any]:
    return {
        "messages": [HumanMessage(content=payload.message)],
        "call_id": call_id,
        "user_id": payload.user_id,
        "conversation_text": payload.message,
        "pre_detected_type": payload.pre_detected_type,
        "pre_detected_risk": payload.pre_detected_risk,
        "execute_tools": payload.execute_tools,
        "demo_mode": demo_mode,
        "detected_scenario": "UNKNOWN",
        "scenario_confidence": 0.0,
        "detected_keywords": [],
        "situation_summary": "",
        "risk_score": 0.0,
        "risk_level": "ABSTAIN",
        "scenario_detail_scores": {},
        "tool_call_reasons": [],
        "tools_to_call": [],
        "tool_results": [],
        "final_actions_taken": [],
        "response_summary": "",
        "error": None,
    }


def _map_graph_result(call_id: str, result: Dict[str, Any]) -> PipelineAOutput:
    messages = result.get("messages", [])
    last_message = messages[-1].content if messages else result.get("response_summary", "응답이 생성되지 않았습니다.")

    history = []
    for msg in messages:
        role = "user" if msg.type == "human" else "assistant"
        history.append({"role": role, "content": msg.content})

    return PipelineAOutput(
        call_id=call_id,
        response=last_message,
        risk_score=result.get("risk_score", 0.0),
        risk_level=result.get("risk_level", "ABSTAIN"),
        detected_scenario=result.get("detected_scenario", "UNKNOWN"),
        scenario_confidence=result.get("scenario_confidence", 0.0),
        detected_keywords=result.get("detected_keywords", []),
        situation_summary=result.get("situation_summary", ""),
        scenario_detail_scores=result.get("scenario_detail_scores", {}),
        tool_call_reasons=result.get("tool_call_reasons", []),
        tools_to_call=result.get("tools_to_call", []),
        tool_results=result.get("tool_results", []),
        final_actions_taken=result.get("final_actions_taken", []),
        history=history,
        error=result.get("error"),
    )


async def _run_graph(payload: PipelineAInput, call_id: str, demo_mode: bool = False) -> PipelineAOutput:
    result = await pipeline_a_graph.ainvoke(_build_initial_state(payload, call_id, demo_mode))
    return _map_graph_result(call_id, result)


async def _push_demo_callback(call_id: str, result: PipelineAOutput) -> None:
    if not settings.SPRING_API_URL:
        return

    url = f"{settings.SPRING_API_URL.rstrip('/')}{settings.SPRING_CALLBACK_PATH}"
    body = {
        "callId": call_id,
        "detectedScenario": result.detected_scenario,
        "riskLevel": result.risk_level,
        "riskScore": result.risk_score,
        "detectedKeywords": result.detected_keywords,
        "situationSummary": result.situation_summary,
        "toolsToCall": result.tools_to_call,
        "finalActionsTaken": result.final_actions_taken,
        "response": result.response,
    }
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.post(
                url,
                json=body,
                headers={
                    "Content-Type": "application/json",
                    "X-Internal-Key": settings.SPRING_INTERNAL_API_KEY,
                },
            )
            response.raise_for_status()
        logger.info("[pipeline_a_demo] callback pushed call_id=%s url=%s", call_id, url)
    except Exception as exc:
        logger.warning("[pipeline_a_demo] callback push failed call_id=%s error=%s", call_id, exc)


async def _process_job(call_id: str, payload: PipelineAInput, demo_mode: bool = False) -> None:
    _JOBS[call_id].update(status="RUNNING", updated_at=_now_iso())
    logger.info(
        "[pipeline_a] job started call_id=%s user_id=%s pre_type=%s pre_risk=%.3f execute_tools=%s demo_mode=%s",
        call_id,
        payload.user_id,
        payload.pre_detected_type,
        payload.pre_detected_risk,
        payload.execute_tools,
        demo_mode,
    )
    try:
        result = await _run_graph(payload, call_id, demo_mode)
        _JOBS[call_id].update(
            status="FAILED" if result.error else "SUCCEEDED",
            tools_to_call=result.tools_to_call,
            final_actions_taken=result.final_actions_taken,
            result=result,
            error=result.error,
            updated_at=_now_iso(),
        )
        logger.info(
            "[pipeline_a] job finished call_id=%s status=%s scenario=%s risk_level=%s risk_score=%.3f tools=%s actions=%s demo_mode=%s",
            call_id,
            "FAILED" if result.error else "SUCCEEDED",
            result.detected_scenario,
            result.risk_level,
            result.risk_score,
            result.tools_to_call,
            result.final_actions_taken,
            demo_mode,
        )
        if demo_mode and result is not None and not result.error:
            await _push_demo_callback(call_id, result)
    except Exception as exc:
        _JOBS[call_id].update(
            status="FAILED",
            tools_to_call=[],
            final_actions_taken=[],
            result=None,
            error=str(exc),
            updated_at=_now_iso(),
        )
        logger.exception("[pipeline_a] job failed call_id=%s error=%s demo_mode=%s", call_id, exc, demo_mode)


@router.post(
    "/runs",
    response_model=PipelineAJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pipeline A 분석 작업 접수",
    description=(
        "Pipeline A 분석 요청을 접수하고 call_id를 즉시 반환합니다. "
        "LangGraph는 백그라운드에서 실행되며 결과는 GET /runs/{call_id}로 조회합니다. "
        "tool 실행은 현재 LangGraph 내부에서 처리하며, tool별 job 조회는 추후 별도로 확장할 수 있습니다."
    ),
)
async def start_pipeline_a_run(
    background_tasks: BackgroundTasks,
    payload: PipelineAInput = Body(..., description="Pipeline A 비동기 분석 요청입니다."),
) -> PipelineAJobAccepted:
    call_id = payload.call_id or str(uuid4())
    if call_id in _JOBS and _JOBS[call_id]["status"] in {"PENDING", "RUNNING"}:
        raise HTTPException(status_code=409, detail="이미 진행 중인 Pipeline A 작업 ID입니다.")

    now = _now_iso()
    _JOBS[call_id] = {
        "call_id": call_id,
        "status": "PENDING",
        "created_at": now,
        "updated_at": now,
        "tools_to_call": [],
        "final_actions_taken": [],
        "result": None,
        "error": None,
    }
    logger.info(
        "[pipeline_a] job accepted call_id=%s user_id=%s pre_type=%s pre_risk=%.3f execute_tools=%s",
        call_id,
        payload.user_id,
        payload.pre_detected_type,
        payload.pre_detected_risk,
        payload.execute_tools,
    )
    background_tasks.add_task(_process_job, call_id, payload, False)
    return PipelineAJobAccepted(
        call_id=call_id,
        status="PENDING",
        status_url=f"/api/v1/pipeline-a/runs/{call_id}",
    )


@router.post(
    "/runs/demo",
    response_model=PipelineAJobAccepted,
    status_code=status.HTTP_202_ACCEPTED,
    summary="Pipeline A 데모 분석 작업 접수",
    description=(
        "Pipeline A 데모 전용 분석 요청을 접수하고 call_id를 즉시 반환합니다. "
        "LLM 단독 분석(룰 기반 키워드 탐지 배제)을 수행하며, 분류는 납치 협박형(KIDNAP_THREAT) 또는 일반 상황(UNKNOWN)으로만 제한됩니다. "
        "외부 도구(FCM, GPS 등)는 DRY_RUN 상태로 실행이 차단됩니다."
    ),
)
async def start_pipeline_a_demo_run(
    background_tasks: BackgroundTasks,
    payload: PipelineADemoInput = Body(..., description="Pipeline A 데모 분석 요청입니다."),
) -> PipelineAJobAccepted:
    call_id = payload.call_id or str(uuid4())
    if call_id in _JOBS and _JOBS[call_id]["status"] in {"PENDING", "RUNNING"}:
        raise HTTPException(status_code=409, detail="이미 진행 중인 Pipeline A 작업 ID입니다.")

    now = _now_iso()
    _JOBS[call_id] = {
        "call_id": call_id,
        "status": "PENDING",
        "created_at": now,
        "updated_at": now,
        "tools_to_call": [],
        "final_actions_taken": [],
        "result": None,
        "error": None,
    }
    logger.info(
        "[pipeline_a_demo] job accepted call_id=%s user_id=%s",
        call_id,
        payload.user_id,
    )

    full_payload = PipelineAInput(
        message=payload.message,
        call_id=call_id,
        user_id=payload.user_id,
        pre_detected_type="UNKNOWN",
        pre_detected_risk=0.0,
        execute_tools=True
    )

    background_tasks.add_task(_process_job, call_id, full_payload, True)
    return PipelineAJobAccepted(
        call_id=call_id,
        status="PENDING",
        status_url=f"/api/v1/pipeline-a/runs/{call_id}",
    )


@router.get(
    "/runs/{call_id}",
    response_model=PipelineAJobStatus,
    summary="Pipeline A 분석 작업 상태 조회",
    description=(
        "POST /runs에서 접수한 Pipeline A 작업의 현재 상태를 반환합니다. "
        "상태가 SUCCEEDED이면 result 필드에 전체 분석 결과가 포함됩니다."
    ),
)
async def get_pipeline_a_run(
    call_id: str = Path(..., description="POST /pipeline-a/runs에서 반환된 call_id입니다.", examples=["call-20260612-0001"]),
) -> PipelineAJobStatus:
    job = _JOBS.get(call_id)
    if not job:
        logger.info("[pipeline_a] job lookup miss call_id=%s", call_id)
        raise HTTPException(status_code=404, detail="Pipeline A 작업을 찾을 수 없습니다.")
    logger.info("[pipeline_a] job lookup call_id=%s status=%s", call_id, job["status"])

    return PipelineAJobStatus(
        call_id=call_id,
        status=job["status"],
        created_at=job["created_at"],
        updated_at=job["updated_at"],
        tools_to_call=job.get("tools_to_call", []),
        final_actions_taken=job.get("final_actions_taken", []),
        result=job.get("result"),
        error=job.get("error"),
    )
