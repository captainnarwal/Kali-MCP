"""Ollama local model provider (OpenAI-compatible tool calling)."""

from __future__ import annotations

import json
from typing import Any

from kali_mcp_client.config import settings
from kali_mcp_client.llm.base import LLMResponse, ToolCall


class OllamaProvider:
    def __init__(
        self,
        host: str | None = None,
        model: str | None = None,
    ) -> None:
        import ollama

        self.model = model or settings.llm_model
        self.client = ollama.AsyncClient(host=host or settings.ollama_host)

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
                        "content": msg.get("content") or "",
                    }
                )
                continue
            if role == "assistant" and msg.get("tool_calls"):
                # Represent prior tool calls in a form Ollama understands
                entry: dict[str, Any] = {
                    "role": "assistant",
                    "content": msg.get("content") or "",
                    "tool_calls": [
                        {
                            "function": {
                                "name": tc["name"],
                                "arguments": tc["arguments"],
                            }
                        }
                        for tc in msg["tool_calls"]
                    ],
                }
                api_messages.append(entry)
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

        response = await self.client.chat(**kwargs)
        message = response.get("message") or {}
        content = message.get("content")
        raw_calls = message.get("tool_calls") or []

        tool_calls: list[ToolCall] = []
        for i, tc in enumerate(raw_calls):
            fn = tc.get("function") or tc
            name = fn.get("name", "")
            args = fn.get("arguments", {})
            if isinstance(args, str):
                try:
                    args = json.loads(args) if args.strip() else {}
                except json.JSONDecodeError:
                    args = {}
            tool_calls.append(
                ToolCall(id=f"ollama_call_{i}", name=name, arguments=dict(args))
            )

        return LLMResponse(content=content, tool_calls=tool_calls, raw=response)
