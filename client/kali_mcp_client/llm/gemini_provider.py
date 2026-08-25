"""Google Gemini provider."""

from __future__ import annotations

import json
from typing import Any

from kali_mcp_client.config import settings
from kali_mcp_client.llm.base import LLMResponse, ToolCall


def _to_gemini_tools(tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Convert OpenAI or Anthropic-style tool defs to Gemini function declarations."""
    declarations: list[dict[str, Any]] = []
    for tool in tools:
        if tool.get("type") == "function" and "function" in tool:
            fn = tool["function"]
            name = fn.get("name", "")
            description = fn.get("description", "")
            parameters = fn.get("parameters") or {"type": "object", "properties": {}}
        else:
            name = tool.get("name", "")
            description = tool.get("description", "")
            parameters = tool.get("input_schema") or tool.get("parameters") or {
                "type": "object",
                "properties": {},
            }
        declarations.append(
            {
                "name": name,
                "description": description,
                "parameters": parameters,
            }
        )
    if not declarations:
        return []
    return [{"function_declarations": declarations}]


def _contents_from_messages(
    messages: list[dict[str, Any]],
) -> tuple[str | None, list[dict[str, Any]]]:
    """Build Gemini contents + optional system instruction from chat messages."""
    system: str | None = None
    contents: list[dict[str, Any]] = []

    for msg in messages:
        role = msg["role"]
        if role == "system":
            system = msg.get("content") or None
            continue

        if role == "tool":
            # Function response — Gemini uses role=user with function_response parts
            contents.append(
                {
                    "role": "user",
                    "parts": [
                        {
                            "function_response": {
                                "name": msg.get("name") or "tool",
                                "response": {"result": msg.get("content") or ""},
                            }
                        }
                    ],
                }
            )
            continue

        if role == "assistant" and msg.get("tool_calls"):
            parts: list[dict[str, Any]] = []
            if msg.get("content"):
                parts.append({"text": msg["content"]})
            for tc in msg["tool_calls"]:
                parts.append(
                    {
                        "function_call": {
                            "name": tc["name"],
                            "args": tc["arguments"] or {},
                        }
                    }
                )
            contents.append({"role": "model", "parts": parts})
            continue

        if role == "assistant":
            contents.append(
                {
                    "role": "model",
                    "parts": [{"text": msg.get("content") or ""}],
                }
            )
            continue

        # user
        contents.append(
            {
                "role": "user",
                "parts": [{"text": msg.get("content") or ""}],
            }
        )

    return system, contents


class GeminiProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from google import genai

        key = api_key or settings.gemini_api_key
        if not key:
            raise ValueError(
                "GEMINI_API_KEY (or GOOGLE_API_KEY) is required for the gemini provider"
            )
        self.model = model or settings.llm_model
        self.client = genai.Client(api_key=key)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        from google.genai import types

        system, contents = _contents_from_messages(messages)
        gemini_tools = _to_gemini_tools(tools)

        config_kwargs: dict[str, Any] = {}
        if system:
            config_kwargs["system_instruction"] = system
        if gemini_tools:
            config_kwargs["tools"] = gemini_tools

        config = types.GenerateContentConfig(**config_kwargs) if config_kwargs else None

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=contents,
            config=config,
        )

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        call_idx = 0

        candidates = getattr(response, "candidates", None) or []
        for cand in candidates:
            content = getattr(cand, "content", None)
            if content is None:
                continue
            for part in getattr(content, "parts", None) or []:
                text = getattr(part, "text", None)
                if text:
                    text_parts.append(text)
                fn = getattr(part, "function_call", None)
                if fn is not None:
                    name = getattr(fn, "name", "") or ""
                    args = getattr(fn, "args", None) or {}
                    if isinstance(args, str):
                        try:
                            args = json.loads(args) if args.strip() else {}
                        except json.JSONDecodeError:
                            args = {}
                    elif hasattr(args, "items"):
                        args = dict(args)
                    else:
                        args = {}
                    tool_calls.append(
                        ToolCall(
                            id=f"gemini_call_{call_idx}",
                            name=name,
                            arguments=args,
                        )
                    )
                    call_idx += 1

        # Fallback to response.text when no structured parts
        if not text_parts and not tool_calls:
            fallback = getattr(response, "text", None)
            if fallback:
                text_parts.append(fallback)

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            raw=response,
        )
