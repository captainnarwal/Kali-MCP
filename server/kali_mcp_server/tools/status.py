"""Server health / capability status tool."""

from __future__ import annotations

from mcp.server import MCPServer

from kali_mcp_server.config import settings
from kali_mcp_server.runner import check_binaries


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def server_status() -> str:
        """Report which Kali tool binaries are installed and whether raw shell is enabled.

        Call this first if a scan tool fails with a missing-binary error.
        """
        status = check_binaries()
        present = [name for name, ok in status.items() if ok]
        missing = [name for name, ok in status.items() if not ok]
        lines = [
            f"ALLOW_RAW={settings.allow_raw}",
            f"default_timeout={settings.default_timeout}",
            f"binaries_present: {', '.join(present) or '(none)'}",
            f"binaries_missing: {', '.join(missing) or '(none)'}",
        ]
        if missing:
            lines.append(
                "Install missing tools on Kali, e.g. "
                "`sudo apt install nmap dirb gobuster nikto enum4linux wpscan "
                "sqlmap hydra john metasploit-framework`"
            )
        return "\n".join(lines)
