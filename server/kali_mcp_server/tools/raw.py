"""Raw shell command tool (gated by ALLOW_RAW)."""

from __future__ import annotations

from mcp.server import MCPServer

from kali_mcp_server.config import settings
from kali_mcp_server.runner import TOOL_EXCEPTION_TYPES, run_shell, tool_error


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def run_command(command: str, timeout: int = 0) -> str:
        """Execute a raw shell command on the Kali host.

        Disabled unless ALLOW_RAW=true is set in the server environment.
        Prefer structured tools (nmap_scan, gobuster_scan, etc.) when possible.

        Args:
            command: Shell command string to execute.
            timeout: Optional timeout in seconds. 0 uses the server default.
        """
        try:
            effective = timeout if timeout and timeout > 0 else settings.default_timeout
            result = await run_shell(command, timeout=effective)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)
