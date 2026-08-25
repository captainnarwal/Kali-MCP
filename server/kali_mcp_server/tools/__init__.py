"""Register all Kali MCP tools on an MCPServer instance."""

from __future__ import annotations

from mcp.server import MCPServer

from kali_mcp_server.tools import exploit, raw, recon, status


def register_tools(mcp: MCPServer) -> None:
    status.register(mcp)
    recon.register(mcp)
    exploit.register(mcp)
    raw.register(mcp)
