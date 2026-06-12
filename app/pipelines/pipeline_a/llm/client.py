import json
import logging
from typing import Any

from langchain_core.messages import BaseMessage
from langchain_openai import ChatOpenAI

from app.core.config import settings

logger = logging.getLogger(__name__)


def get_pipeline_a_llm(*, temperature: float = 0.0, max_tokens: int = 800) -> ChatOpenAI | None:
    """Return the configured OpenAI chat model, or None when the key is not configured."""
    api_key = settings.OPENAI_API_KEY.strip()
    if not api_key or api_key.startswith("your-"):
        return None

    return ChatOpenAI(
        api_key=api_key,
        model=settings.OPENAI_MODEL,
        temperature=temperature,
        max_tokens=max_tokens,
    )


async def invoke_json(messages: list[BaseMessage], *, max_tokens: int = 800) -> dict[str, Any] | None:
    llm = get_pipeline_a_llm(max_tokens=max_tokens)
    if llm is None:
        return None

    try:
        response = await llm.ainvoke(messages)
        raw = str(response.content).strip()
        if raw.startswith("```"):
            raw = raw.strip("`").removeprefix("json").strip()
        return json.loads(raw)
    except Exception as exc:
        logger.warning("[pipeline_a.llm] JSON invocation failed: %s", exc)
        return None
