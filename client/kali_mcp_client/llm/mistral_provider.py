"""Mistral AI provider using the official mistralai SDK."""

from __future__ import annotations

import json
from typing import Any

from kali_mcp_client.config import settings
from kali_mcp_client.llm.base import LLMResponse, ToolCall


def _content_to_str(content: Any) -> str | None:
    if content is None:
        return None
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts: list[str] = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(str(item.get("text") or ""))
            else:
                text = getattr(item, "text", None)
                if text:
                    parts.append(str(text))
        return "".join(parts) if parts else None
    return str(content)


class MistralProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from mistralai.client import Mistral

        key = api_key or settings.mistral_api_key
        if not key:
            raise ValueError("MISTRAL_API_KEY is required for the mistral provider")
        self.model = model or settings.llm_model
        self.client = Mistral(api_key=key)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        api_messages: list[dict[str, Any]] = []
        for msg in messages:
            role = msg["role"]
            if role == "tool":
                api_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": msg["tool_call_id"],
                        "name": msg.get("name") or "",
                        "content": msg.get("content") or "",
                    }
                )
                continue
            if role == "assistant" and msg.get("tool_calls"):
                api_messages.append(
                    {
                        "role": "assistant",
                        "content": msg.get("content"),
                        "tool_calls": [
                            {
                                "id": tc["id"],
                                "type": "function",
                                "function": {
                                    "name": tc["name"],
                                    "arguments": json.dumps(tc["arguments"]),
                                },
                            }
                            for tc in msg["tool_calls"]
                        ],
                    }
                )
                continue
            api_messages.append(
                {"role": role, "content": msg.get("content") or ""}
            )

        kwargs: dict[str, Any] = {
            "model": self.model,
            "messages": api_messages,
        }
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        response = await self.client.chat.complete_async(**kwargs)
        choice = response.choices[0].message

        tool_calls: list[ToolCall] = []
        raw_tool_calls = getattr(choice, "tool_calls", None) or []
        for tc in raw_tool_calls:
            fn = getattr(tc, "function", None)
            name = getattr(fn, "name", "") if fn is not None else ""
            raw_args = getattr(fn, "arguments", None) if fn is not None else None
            if isinstance(raw_args, dict):
                args = raw_args
            elif isinstance(raw_args, str):
                try:
                    args = json.loads(raw_args or "{}")
                except json.JSONDecodeError:
                    args = {}
            else:
                args = {}
            tool_calls.append(
                ToolCall(
                    id=getattr(tc, "id", "") or f"mistral_call_{len(tool_calls)}",
                    name=name,
                    arguments=args,
                )
            )

        return LLMResponse(
            content=_content_to_str(getattr(choice, "content", None)),
            tool_calls=tool_calls,
            raw=response,
        )
