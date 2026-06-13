import json
import logging
import os
from typing import Any

from app.core.config import settings

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

logger = logging.getLogger(__name__)


def get_pipeline_a_llm(*, temperature: float = 0.0, max_tokens: int = 800) -> ChatOpenAI | None:
    """Return the configured OpenAI chat model, or None when the key is not configured.
    Routes through the custom base URL if configured (e.g. GMS OpenRouter).
    """
    logger.info(
        "LangSmith ENV Check: TRACING=%s, ENDPOINT=%s, PROJECT=%s, API_KEY_exists=%s",
        os.getenv("LANGCHAIN_TRACING_V2"),
        os.getenv("LANGCHAIN_ENDPOINT"),
        os.getenv("LANGCHAIN_PROJECT"),
        bool(os.getenv("LANGCHAIN_API_KEY")),
    )

    api_key = settings.OPENAI_API_KEY.strip()
    if not api_key or api_key.startswith("your-"):
        return None

    base_url = settings.OPENAI_API_BASE.strip() if settings.OPENAI_API_BASE else None

    # gpt-5-nano is a reasoning model. Reasoning tokens are counted towards max_tokens,
    # so we must increase the limit to at least 4096 to prevent truncation.
    if settings.OPENAI_MODEL == "gpt-5-nano":
        max_tokens = max(max_tokens, 4096)


    return ChatOpenAI(
        api_key=api_key,
        base_url=base_url or None,
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