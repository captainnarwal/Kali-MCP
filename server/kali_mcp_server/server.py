"""Kali MCP server entrypoint — Streamable HTTP, no LLM."""

from __future__ import annotations

import logging
import secrets

import uvicorn
from mcp.server import MCPServer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from kali_mcp_server.config import settings
from kali_mcp_server.runner import check_binaries
from kali_mcp_server.tools import register_tools

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("kali_mcp_server")

mcp = MCPServer(
    "kali-mcp",
    instructions=(
        "Kali Linux pentest/DAST tool server. Use only against systems you are "
        "authorized to test. Tools wrap nmap, dirb, gobuster, nikto, enum4linux, "
        "wpscan, sqlmap, hydra, john, metasploit, and optional raw commands."
    ),
)

register_tools(mcp)


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Reject requests missing a valid Bearer token when auth is configured."""

    async def dispatch(self, request: Request, call_next) -> Response:
        token = settings.auth_token
        if not token:
            return await call_next(request)

        # Allow unauthenticated health-style probes on root if desired; MCP is under /mcp
        auth_header = request.headers.get("authorization", "")
        expected = f"Bearer {token}"
        # Constant-time compare when lengths match
        if len(auth_header) != len(expected) or not secrets.compare_digest(
            auth_header, expected
        ):
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        return await call_next(request)


def create_app():
    """Build the ASGI app with optional bearer auth middleware."""
    # Prefer streamable_http_app; fall back to sse_app naming across SDK versions
    if hasattr(mcp, "streamable_http_app"):
        app = mcp.streamable_http_app()
    elif hasattr(mcp, "http_app"):
        app = mcp.http_app()
    else:
        raise RuntimeError(
            "This mcp SDK version does not expose a Streamable HTTP ASGI app. "
            "Upgrade mcp: pip install -U mcp"
        )

    if settings.auth_token:
        app.add_middleware(BearerAuthMiddleware)
        logger.info("Bearer token authentication is ENABLED")
    else:
        logger.warning(
            "MCP_AUTH_TOKEN is empty — authentication DISABLED. "
            "Do not expose this server on untrusted networks."
        )
    return app


def main() -> None:
    status = check_binaries()
    present = [name for name, ok in status.items() if ok]
    missing = [name for name, ok in status.items() if not ok]
    logger.info("Tool binaries present: %s", ", ".join(present) or "(none)")
    if missing:
        logger.warning("Tool binaries missing: %s", ", ".join(missing))
    logger.info("ALLOW_RAW=%s", settings.allow_raw)
    logger.info(
        "Starting Kali MCP on http://%s:%s/mcp", settings.host, settings.port
    )

    app = create_app()
    uvicorn.run(app, host=settings.host, port=settings.port, log_level="info")


if __name__ == "__main__":
    main()
