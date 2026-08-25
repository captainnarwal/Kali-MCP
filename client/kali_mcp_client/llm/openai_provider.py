"""OpenAI Chat Completions provider."""

from __future__ import annotations

import json
from typing import Any

from kali_mcp_client.config import settings
from kali_mcp_client.llm.base import LLMResponse, ToolCall


class OpenAIProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        key = api_key or settings.openai_api_key
        if not key:
            raise ValueError("OPENAI_API_KEY is required for the openai provider")
        self.model = model or settings.llm_model
        self.client = AsyncOpenAI(api_key=key)

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

        response = await self.client.chat.completions.create(**kwargs)
        choice = response.choices[0].message

        tool_calls: list[ToolCall] = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append(
                    ToolCall(id=tc.id, name=tc.function.name, arguments=args)
                )

        return LLMResponse(
            content=choice.content,
            tool_calls=tool_calls,
            raw=response,
        )
