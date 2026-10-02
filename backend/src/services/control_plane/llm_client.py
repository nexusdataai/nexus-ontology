"""
LLM Client for the AI Control Plane.

Provides an abstracted interface to OpenAI chat completions.
Supports system prompts, tool/function definitions, and streaming.
Designed to be swappable for Bedrock/Anthropic in the future.
"""

import os
import json
from typing import Any, Dict, List, Optional

from loguru import logger

try:
    import openai
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

from .embedding_service import _get_openai_key

cp_logger = logger.bind(component="control-plane")

DEFAULT_MODEL = "gpt-4o-mini"
MAX_TOKENS_DEFAULT = 2048


class LLMClient:
    """Chat completions client wrapping OpenAI (sync + async)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        # An explicit caller-supplied key is honored for the lifetime of the
        # instance. When None (the common case for the get_llm_client()
        # singleton), the key is resolved fresh via _get_openai_key() on
        # every access so AWS Secrets Manager rotations propagate without
        # requiring a process restart.
        self._explicit_api_key = api_key
        self._model = model
        self._client = None
        self._async_client = None
        # Track which key the cached openai.OpenAI clients were constructed
        # with so we can detect rotation and rebuild only when needed.
        self._client_key: Optional[str] = None
        self._async_client_key: Optional[str] = None

    @property
    def _api_key(self) -> Optional[str]:
        return self._explicit_api_key or _get_openai_key()

    @property
    def available(self) -> bool:
        return OPENAI_AVAILABLE and bool(self._api_key)

    def _ensure_client(self):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package not installed")
        key = self._api_key
        if not key:
            raise RuntimeError("OpenAI API key not configured")
        if self._client is None or self._client_key != key:
            self._client = openai.OpenAI(api_key=key)
            self._client_key = key

    def _ensure_async_client(self):
        if not OPENAI_AVAILABLE:
            raise RuntimeError("openai package not installed")
        key = self._api_key
        if not key:
            raise RuntimeError("OpenAI API key not configured")
        if self._async_client is None or self._async_client_key != key:
            self._async_client = openai.AsyncOpenAI(api_key=key)
            self._async_client_key = key

    @staticmethod
    def _parse_response(resp) -> Dict[str, Any]:
        choice = resp.choices[0]
        result: Dict[str, Any] = {
            "content": choice.message.content or "",
            "role": choice.message.role,
            "finish_reason": choice.finish_reason,
            "usage": {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            },
        }
        if choice.message.tool_calls:
            result["tool_calls"] = [
                {
                    "id": tc.id,
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments,
                    },
                }
                for tc in choice.message.tool_calls
            ]
        return result

    def _build_kwargs(self, messages, max_tokens, temperature, tools):
        kwargs: Dict[str, Any] = {
            "model": self._model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"
        return kwargs

    def chat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = 0.1,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        self._ensure_client()
        kwargs = self._build_kwargs(messages, max_tokens, temperature, tools)
        resp = self._client.chat.completions.create(**kwargs)
        return self._parse_response(resp)

    async def achat(
        self,
        messages: List[Dict[str, str]],
        max_tokens: int = MAX_TOKENS_DEFAULT,
        temperature: float = 0.1,
        tools: Optional[List[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """Async chat completion -- does not block the event loop."""
        self._ensure_async_client()
        kwargs = self._build_kwargs(messages, max_tokens, temperature, tools)
        resp = await self._async_client.chat.completions.create(**kwargs)
        return self._parse_response(resp)


_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    global _client
    if _client is None:
        _client = LLMClient()
    return _client
