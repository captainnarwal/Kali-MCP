"""AI agent loop: LLM tool-calling <-> Kali MCP tools."""

from __future__ import annotations

import logging
from typing import Any

from kali_mcp_client.config import settings
from kali_mcp_client.llm.base import LLMProvider
from kali_mcp_client.mcp_client import KaliMCPClient

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an authorized penetration-testing assistant connected to a Kali Linux MCP server.
You help the user run reconnaissance and DAST tools (nmap, dirb, gobuster, nikto, enum4linux, wpscan, sqlmap, hydra, john, metasploit) and optional raw commands.

Rules:
- Only operate on targets the user explicitly authorizes in this conversation.
- Prefer structured MCP tools over raw shell when a dedicated tool exists.
- Explain what you are about to run and summarize results clearly.
- If a tool fails (missing binary, timeout, auth error), report the error and suggest fixes.
- Do not invent scan results; base answers on tool output.
- Refuse requests that clearly target systems the user does not own or have permission to test.
"""


class Agent:
    def __init__(
        self,
        mcp: KaliMCPClient,
        llm: LLMProvider,
        *,
        max_turns: int | None = None,
    ) -> None:
        self.mcp = mcp
        self.llm = llm
        self.max_turns = max_turns or settings.max_agent_turns
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]
        self._openai_tools: list[dict[str, Any]] = []
        self._anthropic_tools: list[dict[str, Any]] = []
        self._provider_name = settings.llm_provider

    async def setup(self) -> list[str]:
        tools = await self.mcp.list_tools()
        self._openai_tools = self.mcp.tools_for_openai(tools)
        self._anthropic_tools = self.mcp.tools_for_anthropic(tools)
        return [t["name"] for t in tools]

    def _tools_for_provider(self) -> list[dict[str, Any]]:
        if self._provider_name == "anthropic":
            return self._anthropic_tools
        if self._provider_name in {"gemini", "google"}:
            # Gemini provider accepts Anthropic-style {name, description, input_schema}
            return self._anthropic_tools
        # openai + mistral + ollama (OpenAI-compatible tool schema)
        return self._openai_tools

    async def run_turn(self, user_text: str) -> str:
        self.messages.append({"role": "user", "content": user_text})
        tools = self._tools_for_provider()

        for turn in range(self.max_turns):
            logger.debug("Agent LLM turn %s", turn + 1)
            response = await self.llm.chat(self.messages, tools)

            if response.has_tool_calls:
                # Record assistant tool-call message
                self.messages.append(
                    {
                        "role": "assistant",
                        "content": response.content,
                        "tool_calls": [
                            {
                                "id": tc.id,
                                "name": tc.name,
                                "arguments": tc.arguments,
                            }
                            for tc in response.tool_calls
                        ],
                    }
                )
                for tc in response.tool_calls:
                    try:
                        result_text = await self.mcp.call_tool(tc.name, tc.arguments)
                    except Exception as exc:  # noqa: BLE001 — surface to LLM
                        result_text = f"Error calling tool {tc.name}: {exc}"
                    self.messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tc.id,
                            "name": tc.name,
                            "content": result_text,
                        }
                    )
                continue

            # Final text answer
            final = (response.content or "").strip() or "(no response)"
            self.messages.append({"role": "assistant", "content": final})
            return final

        return (
            "Stopped: reached MAX_AGENT_TURNS without a final answer. "
            "Increase MAX_AGENT_TURNS or narrow the request."
        )

    def reset(self) -> None:
        self.messages = [{"role": "system", "content": SYSTEM_PROMPT}]
