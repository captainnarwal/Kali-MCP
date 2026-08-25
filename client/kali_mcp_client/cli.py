"""Interactive CLI REPL for the Kali MCP AI agent."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from kali_mcp_client.agent import Agent
from kali_mcp_client.config import settings
from kali_mcp_client.llm import create_provider
from kali_mcp_client.logging_config import setup_logging
from kali_mcp_client.mcp_client import KaliMCPClient

logger = logging.getLogger("kali_mcp_client")


BANNER = """
╔══════════════════════════════════════════════════════════╗
║              Kali MCP AI Agent (client)                  ║
║  Type your request. Commands: /tools /reset /quit        ║
║  Authorized testing only — you are responsible for scope ║
╚══════════════════════════════════════════════════════════╝
"""


async def repl(server_url: str | None = None) -> int:
    print(BANNER)
    print(f"Provider: {settings.llm_provider}  Model: {settings.llm_model}")
    print(f"Server:   {server_url or settings.server_url}")
    print()

    try:
        llm = create_provider()
    except Exception as exc:
        print(f"Failed to initialize LLM provider: {exc}", file=sys.stderr)
        return 1

    mcp = KaliMCPClient(server_url=server_url)
    try:
        await mcp.connect()
    except Exception as exc:
        print(f"Failed to connect to MCP server: {exc}", file=sys.stderr)
        print(
            "Is the server running? Check MCP_SERVER_URL and MCP_AUTH_TOKEN.",
            file=sys.stderr,
        )
        print(
            "HTTP 421 usually means the server rejected the Host header "
            "(common with a WSL/LAN IP). Restart the Kali server after updating "
            "it, or set MCP_ALLOWED_HOSTS on the server to that IP.",
            file=sys.stderr,
        )
        return 1

    agent = Agent(mcp, llm)
    try:
        tool_names = await agent.setup()
        print(f"Loaded {len(tool_names)} tools: {', '.join(tool_names)}\n")
    except Exception as exc:
        print(f"Failed to list tools: {exc}", file=sys.stderr)
        await mcp.close()
        return 1

    try:
        while True:
            try:
                user_text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye.")
                break

            if not user_text:
                continue
            if user_text.lower() in {"/quit", "/exit", "quit", "exit"}:
                print("Bye.")
                break
            if user_text.lower() == "/reset":
                agent.reset()
                print("(conversation reset)\n")
                continue
            if user_text.lower() == "/tools":
                names = await agent.setup()
                print("Tools: " + ", ".join(names) + "\n")
                continue

            print("agent> (thinking / running tools...)")
            try:
                reply = await agent.run_turn(user_text)
            except Exception as exc:
                logger.exception("Agent turn failed")
                print(f"agent> Error: {exc}\n")
                continue
            print(f"agent> {reply}\n")
    finally:
        await mcp.close()

    return 0


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description="Kali MCP AI agent client")
    parser.add_argument(
        "--server",
        default=None,
        help="MCP server URL (default: MCP_SERVER_URL from env)",
    )
    parser.add_argument(
        "-v",
        "--verbose",
        action="store_true",
        help="Enable debug logging",
    )
    args = parser.parse_args(argv)

    level = "DEBUG" if args.verbose else settings.log_level
    setup_logging(
        log_dir=settings.log_dir,
        level=level,
        max_bytes=settings.log_max_bytes,
        backup_count=settings.log_backup_count,
    )

    raise SystemExit(asyncio.run(repl(server_url=args.server)))


if __name__ == "__main__":
    main()
