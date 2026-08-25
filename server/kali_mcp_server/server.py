"""Kali MCP server entrypoint — Streamable HTTP, no LLM."""

from __future__ import annotations

import secrets

import uvicorn
from mcp.server import MCPServer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from kali_mcp_server.config import settings
from kali_mcp_server.logging_config import setup_logging
from kali_mcp_server.runner import check_binaries
from kali_mcp_server.tools import register_tools

_LOOPBACK_HOSTS = (
    "localhost",
    "localhost:*",
    "127.0.0.1",
    "127.0.0.1:*",
    "[::1]",
    "[::1]:*",
)
_LOOPBACK_BIND = {"127.0.0.1", "localhost", "::1", "[::1]"}

logger = setup_logging(
    log_dir=settings.log_dir,
    level=settings.log_level,
    max_bytes=settings.log_max_bytes,
    backup_count=settings.log_backup_count,
)

mcp = MCPServer(
    "kali-mcp",
    instructions=(
        "Kali Linux pentest/DAST tool server. Use only against systems you are "
        "authorized to test. Tools wrap nmap, dirb, gobuster, nikto, enum4linux, "
        "wpscan, sqlmap, hydra, john, metasploit, and optional raw commands. "
        "For host scanners (nmap, enum4linux, hydra) pass a hostname or IP — "
        "not a full http(s) URL. If a tool returns TOOL ERROR about a missing "
        "binary, call server_status and tell the user to install the package on Kali. "
        "Never invent or simulate scan output."
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


def _with_port_wildcard(host: str) -> list[str]:
    """Accept Host with or without an explicit port for a hostname or IPv4/IPv6."""
    host = host.strip()
    if not host:
        return []
    if host.endswith(":*") or host == "*":
        return [host]
    if host.startswith("["):
        if host.endswith("]"):
            return [host, f"{host}:*"]
        return [host]
    if host.count(":") == 1:
        return [host]
    return [host, f"{host}:*"]


def _transport_security():
    """Configure MCP DNS-rebinding protection for LAN/WSL hosts.

    Without this, connecting via a non-localhost IP (e.g. a WSL address) is
    rejected with HTTP 421 Misdirected Request / Invalid Host header.
    """
    try:
        from mcp.server.transport_security import TransportSecuritySettings
    except ImportError:
        return None

    extra: list[str] = []
    for host in settings.allowed_hosts:
        extra.extend(_with_port_wildcard(host))

    origins = list(settings.allowed_origins)
    if extra:
        hosts = list(dict.fromkeys([*_LOOPBACK_HOSTS, *extra]))
        logger.info("DNS rebinding protection ENABLED; allowed hosts: %s", hosts)
        kwargs: dict = {
            "enable_dns_rebinding_protection": True,
            "allowed_hosts": hosts,
        }
        if origins:
            kwargs["allowed_origins"] = origins
        return TransportSecuritySettings(**kwargs)

    if settings.host in _LOOPBACK_BIND:
        return None

    logger.warning(
        "DNS rebinding protection DISABLED (MCP_HOST=%s). "
        "Set MCP_ALLOWED_HOSTS to your client-facing IP or hostname "
        "(for example the WSL address) to keep Host-header checks on.",
        settings.host,
    )
    return TransportSecuritySettings(enable_dns_rebinding_protection=False)


def _call_app_builder(builder, *, transport_security):
    """Invoke streamable_http_app/http_app across mcp SDK versions."""
    attempts: list[dict] = []
    if transport_security is not None:
        attempts.append({"transport_security": transport_security})
    elif settings.host not in _LOOPBACK_BIND:
        # Non-localhost bind: host= tells older SDKs not to lock Host to localhost.
        attempts.append({"host": settings.host})
    attempts.append({})
    last_error: TypeError | None = None
    for kwargs in attempts:
        try:
            return builder(**kwargs)
        except TypeError as exc:
            last_error = exc
            continue
    if last_error is not None:
        raise last_error
    return builder()


def create_app():
    """Build the ASGI app with optional bearer auth middleware."""
    security = _transport_security()
    # Prefer streamable_http_app; fall back to sse_app naming across SDK versions
    if hasattr(mcp, "streamable_http_app"):
        app = _call_app_builder(mcp.streamable_http_app, transport_security=security)
    elif hasattr(mcp, "http_app"):
        app = _call_app_builder(mcp.http_app, transport_security=security)
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
