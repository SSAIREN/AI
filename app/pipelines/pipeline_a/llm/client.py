import json
import logging
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_pipeline_a_llm(*, temperature: float = 0.0, max_tokens: int = 800) -> ChatOpenAI | None:
    """Return the configured OpenAI chat model, or None when the key is not configured.
    If a Google Gemini key is detected, it automatically routes through Gemini's OpenAI-compatible endpoint.
    """
    api_key = settings.OPENAI_API_KEY.strip()
    if not api_key or api_key.startswith("your-"):
        return None

    if api_key.startswith("AIzaSy"):
        # Gemini's thinking/reasoning tokens are counted towards max_tokens in the compatibility layer.
        # We increase max_tokens to at least 2048 to prevent LengthFinishReasonError.
        gemini_max_tokens = max(max_tokens, 2048)
        return ChatOpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
            model="gemini-3.5-flash",
            temperature=temperature,
            max_tokens=gemini_max_tokens,
            model_kwargs={"response_format": {"type": "json_object"}},
        )

    return ChatOpenAI(
        api_key=api_key,
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
    )

import re

async def invoke_json(messages: list[BaseMessage], *, max_tokens: int = 800) -> dict[str, Any] | None:
    llm = get_pipeline_a_llm(max_tokens=max_tokens)
    if llm is None:
        return None

    try:
        response = await llm.ainvoke(messages)
        raw = str(response.content).strip()

        # 코드블록 제거
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()

        # trailing comma 제거 (}, ] 앞의 쉼표)
        raw = re.sub(r",\s*([}\]])", r"\1", raw)

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            # JSON 객체 부분만 추출 시도
            match = re.search(r"\{.*\}", raw, re.DOTALL)
            if match:
                cleaned = re.sub(r",\s*([}\]])", r"\1", match.group())
                return json.loads(cleaned)
            raise
    except Exception as exc:
        logger.warning("[pipeline_a.llm] JSON invocation failed: %s", exc)
        logger.debug("[pipeline_a.llm] raw response: %r", raw if 'raw' in locals() else None)
        return None