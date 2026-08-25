"""MCP Streamable HTTP client wrapper for the Kali server."""

from __future__ import annotations

import json
import logging
from contextlib import AsyncExitStack
from typing import Any

from kali_mcp_client.config import settings

logger = logging.getLogger(__name__)


def _make_http_client(headers: dict[str, str]):
    """Create an async HTTP client compatible with the installed mcp SDK."""
    timeout_read = 600.0
    try:
        import httpx2 as http_lib

        return http_lib.AsyncClient(
            headers=headers or None,
            timeout=http_lib.Timeout(30.0, read=timeout_read),
            follow_redirects=True,
        )
    except ImportError:
        import httpx as http_lib

        return http_lib.AsyncClient(
            headers=headers or None,
            timeout=http_lib.Timeout(30.0, read=timeout_read),
            follow_redirects=True,
        )


def _import_streamable_client():
    """Import streamable HTTP client across mcp SDK versions."""
    try:
        from mcp.client.streamable_http import streamable_http_client

        return streamable_http_client, "v2"
    except ImportError:
        from mcp.client.streamable_http import streamablehttp_client

        return streamablehttp_client, "v1"


class KaliMCPClient:
    """Connects to the Kali MCP server and exposes list/call tool helpers."""

    def __init__(
        self,
        server_url: str | None = None,
        auth_token: str | None = None,
    ) -> None:
        self.server_url = server_url or settings.server_url
        self.auth_token = auth_token if auth_token is not None else settings.auth_token
        self._stack: AsyncExitStack | None = None
        self._session = None
        self._tools_cache: list[dict[str, Any]] | None = None

    async def __aenter__(self) -> KaliMCPClient:
        await self.connect()
        return self

    async def __aexit__(self, *exc: object) -> None:
        await self.close()

    async def connect(self) -> None:
        from mcp import ClientSession

        streamable_client, api_ver = _import_streamable_client()
        self._stack = AsyncExitStack()
        await self._stack.__aenter__()

        try:
            headers: dict[str, str] = {}
            if self.auth_token:
                headers["Authorization"] = f"Bearer {self.auth_token}"

            if api_ver == "v2":
                http_client = _make_http_client(headers)
                await self._stack.enter_async_context(http_client)
                streams = await self._stack.enter_async_context(
                    streamable_client(self.server_url, http_client=http_client)
                )
                if isinstance(streams, tuple) and len(streams) >= 2:
                    read_stream, write_stream = streams[0], streams[1]
                else:
                    raise RuntimeError("Unexpected streamable_http_client return value")
            else:
                streams = await self._stack.enter_async_context(
                    streamable_client(self.server_url, headers=headers)
                )
                read_stream, write_stream = streams[0], streams[1]

            self._session = await self._stack.enter_async_context(
                ClientSession(read_stream, write_stream)
            )
            await self._session.initialize()
        except BaseException:
            try:
                await self.close()
            except Exception:
                logger.debug("Error while closing after failed connect", exc_info=True)
            raise
        logger.info("Connected to MCP server at %s", self.server_url)

    async def close(self) -> None:
        if self._stack is not None:
            await self._stack.aclose()
            self._stack = None
            self._session = None
            self._tools_cache = None

    def _require_session(self):
        if self._session is None:
            raise RuntimeError("Not connected. Call connect() or use async with.")
        return self._session

    async def list_tools(self, *, refresh: bool = False) -> list[dict[str, Any]]:
        """Return tools as OpenAI-style function schemas (also usable by Anthropic)."""
        if self._tools_cache is not None and not refresh:
            return self._tools_cache

        session = self._require_session()
        result = await session.list_tools()
        tools: list[dict[str, Any]] = []
        for tool in result.tools:
            schema = (
                getattr(tool, "input_schema", None)
                or getattr(tool, "inputSchema", None)
                or {
                    "type": "object",
                    "properties": {},
                }
            )
            tools.append(
                {
                    "name": tool.name,
                    "description": tool.description or "",
                    "input_schema": schema,
                }
            )
        self._tools_cache = tools
        return tools

    async def call_tool(self, name: str, arguments: dict[str, Any] | None = None) -> str:
        """Invoke an MCP tool and return concatenated text content."""
        session = self._require_session()
        arguments = arguments or {}
        logger.info("Calling MCP tool %s(%s)", name, arguments)
        result = await session.call_tool(name, arguments)

        parts: list[str] = []
        for block in result.content or []:
            text = getattr(block, "text", None)
            if text is not None:
                parts.append(text)
            else:
                parts.append(str(block))

        if getattr(result, "is_error", None) or getattr(result, "isError", False):
            err = "TOOL ERROR:\n" + ("\n".join(parts) if parts else "(no details)")
            logger.warning("MCP tool %s error: %s", name, err[:500])
            return err

        text = "\n".join(parts) if parts else json.dumps(
            {"status": "ok", "content": str(result.content)}
        )
        if text.startswith("TOOL ERROR"):
            logger.warning("MCP tool %s returned error: %s", name, text[:500])
        return text

    def tools_for_openai(self, tools: list[dict[str, Any]] | None = None) -> list[dict]:
        tools = tools if tools is not None else (self._tools_cache or [])
        return [
            {
                "type": "function",
                "function": {
                    "name": t["name"],
                    "description": t["description"],
                    "parameters": t["input_schema"],
                },
            }
            for t in tools
        ]

    def tools_for_anthropic(self, tools: list[dict[str, Any]] | None = None) -> list[dict]:
        tools = tools if tools is not None else (self._tools_cache or [])
        return [
            {
                "name": t["name"],
                "description": t["description"],
                "input_schema": t["input_schema"],
            }
            for t in tools
        ]

    def tools_for_ollama(self, tools: list[dict[str, Any]] | None = None) -> list[dict]:
        return self.tools_for_openai(tools)
