from typing import Any, Dict

import httpx

from app.core.config import settings


def dry_run(tool: str, **payload: Any) -> Dict[str, Any]:
    return {
        "tool": tool,
        "status": "DRY_RUN",
        "message": "External Spring integration is not configured or execute_tools is false.",
        "payload": {
            "call_id": payload.get("call_id"),
            "user_id": payload.get("user_id"),
            "detected_scenario": payload.get("detected_scenario"),
            "risk_score": payload.get("risk_score"),
        },
    }


def can_call_external(execute_tools: bool) -> bool:
    return bool(execute_tools and settings.SPRING_API_URL and settings.SPRING_INTERNAL_API_KEY)


async def get(path: str, *, execute_tools: bool, params: Dict[str, Any] | None = None) -> Dict[str, Any]:
    if not can_call_external(execute_tools):
        return dry_run(f"GET {path}", **(params or {}))

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
