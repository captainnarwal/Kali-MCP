"""Anthropic Claude provider."""

from __future__ import annotations

import json
from typing import Any

from kali_mcp_client.config import settings
from kali_mcp_client.llm.base import LLMResponse, ToolCall


class AnthropicProvider:
    def __init__(
        self,
        api_key: str | None = None,
        model: str | None = None,
    ) -> None:
        from anthropic import AsyncAnthropic

        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is required for the anthropic provider")
        self.model = model or settings.llm_model
        self.client = AsyncAnthropic(api_key=key)

    async def chat(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
    ) -> LLMResponse:
        system = ""
        api_messages: list[dict[str, Any]] = []
        i = 0
        while i < len(messages):
            msg = messages[i]
            role = msg["role"]
            if role == "system":
                system = msg.get("content") or ""
                i += 1
                continue
            if role == "tool":
                # Anthropic expects all tool_results for a turn in one user message
                blocks: list[dict[str, Any]] = []
                while i < len(messages) and messages[i]["role"] == "tool":
                    tmsg = messages[i]
                    blocks.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": tmsg["tool_call_id"],
                            "content": tmsg.get("content") or "",
                        }
                    )
                    i += 1
                api_messages.append({"role": "user", "content": blocks})
                continue
            if role == "assistant" and msg.get("tool_calls"):
                content_blocks: list[dict[str, Any]] = []
                if msg.get("content"):
                    content_blocks.append({"type": "text", "text": msg["content"]})
                for tc in msg["tool_calls"]:
                    content_blocks.append(
                        {
                            "type": "tool_use",
                            "id": tc["id"],
                            "name": tc["name"],
                            "input": tc["arguments"],
                        }
                    )
                api_messages.append({"role": "assistant", "content": content_blocks})
                i += 1
                continue
            api_messages.append(
                {"role": role, "content": msg.get("content") or ""}
            )
            i += 1

        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": 8096,
            "messages": api_messages,
        }
        if system:
            kwargs["system"] = system
        if tools:
            kwargs["tools"] = tools

        response = await self.client.messages.create(**kwargs)

        text_parts: list[str] = []
        tool_calls: list[ToolCall] = []
        for block in response.content:
            btype = getattr(block, "type", None)
            if btype == "text":
                text_parts.append(block.text)
            elif btype == "tool_use":
                tool_calls.append(
                    ToolCall(
                        id=block.id,
                        name=block.name,
                        arguments=dict(block.input or {}),
                    )
                )

        return LLMResponse(
            content="\n".join(text_parts) if text_parts else None,
            tool_calls=tool_calls,
            raw=response,
        )


def ensure_json_args(arguments: Any) -> dict[str, Any]:
    if isinstance(arguments, dict):
        return arguments
    if isinstance(arguments, str):
        return json.loads(arguments) if arguments.strip() else {}
    return {}
