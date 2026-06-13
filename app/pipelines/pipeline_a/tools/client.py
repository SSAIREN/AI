import logging
from typing import Any, Dict

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


def dry_run(tool: str, **payload: Any) -> Dict[str, Any]:
    logger.info(
        "[pipeline_a.tool_client] dry_run tool=%s session_id=%s payload_keys=%s",
        tool,
        payload.get("session_id") or payload.get("sessionId"),
        sorted(payload.keys()),
    )
    return {
        "tool": tool,
        "status": "DRY_RUN",
        "message": "External Spring integration is not configured or execute_tools is false.",
        "payload": {
            "session_id": payload.get("session_id"),
            "detected_scenario": payload.get("detected_scenario"),
            "risk_score": payload.get("risk_score"),
        },
    }


def can_call_external(execute_tools: bool) -> bool:
    return bool(execute_tools and settings.SPRING_API_URL and settings.SPRING_INTERNAL_API_KEY)


async def get(path: str, *, execute_tools: bool, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not can_call_external(execute_tools):
        return dry_run(f"GET {path}", **(params or {}))

    logger.info("[pipeline_a.tool_client] GET %s params=%s", path, params)
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        response = await client.get(
            f"{settings.SPRING_API_URL.rstrip('/')}{path}",
            params=params,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Key": settings.SPRING_INTERNAL_API_KEY,
            },
        )
        response.raise_for_status()
        return response.json()


async def post(path: str, *, execute_tools: bool, body: Dict[str, Any]) -> Dict[str, Any]:
    if not can_call_external(execute_tools):
        return dry_run(f"POST {path}", **body)

    logger.info("[pipeline_a.tool_client] POST %s body_keys=%s", path, sorted(body.keys()))
    async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
        response = await client.post(
            f"{settings.SPRING_API_URL.rstrip('/')}{path}",
            json=body,
            headers={
                "Content-Type": "application/json",
                "X-Internal-Key": settings.SPRING_INTERNAL_API_KEY,
            },
        )
        response.raise_for_status()
        return response.json()
