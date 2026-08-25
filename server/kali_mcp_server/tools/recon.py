"""Reconnaissance / DAST MCP tools."""

from __future__ import annotations

from mcp.server import MCPServer

from kali_mcp_server.runner import (
    TOOL_EXCEPTION_TYPES,
    normalize_host_target,
    resolve_binary,
    run_argv,
    split_extra_args,
    tool_error,
)


def register(mcp: MCPServer) -> None:
    @mcp.tool()
    async def nmap_scan(target: str, extra_args: str = "") -> str:
        """Run an Nmap scan against a host or network.

        Args:
            target: Hostname, IP, or CIDR range to scan (not a full URL; http:// is stripped).
            extra_args: Optional extra nmap flags (e.g. '-sV -p 1-1000').
        """
        try:
            host = normalize_host_target(target)
            binary = resolve_binary("nmap")
            argv = [binary, *split_extra_args(extra_args), host]
            result = await run_argv(argv)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)

    @mcp.tool()
    async def dirb_scan(url: str, wordlist: str = "") -> str:
        """Run Dirb directory brute-force against a web URL.

        Args:
            url: Target URL (e.g. http://example.com/).
            wordlist: Optional path to a wordlist file. Uses dirb default if empty.
        """
        try:
            binary = resolve_binary("dirb")
            argv = [binary, url]
            if wordlist:
                argv.append(wordlist)
            result = await run_argv(argv)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)

    @mcp.tool()
    async def gobuster_scan(
        url: str, mode: str = "dir", wordlist: str = "", extra_args: str = ""
    ) -> str:
        """Run Gobuster (dir/dns/vhost/etc.) against a target.

        Args:
            url: Target URL or domain depending on mode.
            mode: Gobuster mode (dir, dns, vhost, fuzz, s3, gcs, tftp). Default dir.
            wordlist: Path to wordlist. Recommended for dir mode.
            extra_args: Optional extra gobuster flags.
        """
        try:
            binary = resolve_binary("gobuster")
            argv = [binary, mode, "-u", url, *split_extra_args(extra_args)]
            if wordlist:
                argv.extend(["-w", wordlist])
            result = await run_argv(argv)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)

    @mcp.tool()
    async def nikto_scan(target: str, extra_args: str = "") -> str:
        """Run Nikto web server scanner.

        Args:
            target: Hostname or URL to scan.
            extra_args: Optional extra nikto flags.
        """
        try:
            binary = resolve_binary("nikto")
            argv = [binary, "-h", target, *split_extra_args(extra_args)]
            result = await run_argv(argv)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)

    @mcp.tool()
    async def enum4linux_scan(target: str, extra_args: str = "") -> str:
        """Run enum4linux against a Windows/Samba host.

        Args:
            target: Target IP or hostname.
            extra_args: Optional extra enum4linux flags (e.g. '-a').
        """
        try:
            host = normalize_host_target(target)
            binary = resolve_binary("enum4linux")
            extras = split_extra_args(extra_args)
            if extras:
                argv = [binary, *extras, host]
            else:
                argv = [binary, "-a", host]
            result = await run_argv(argv)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)

    @mcp.tool()
    async def wpscan_scan(url: str, extra_args: str = "") -> str:
        """Run WPScan against a WordPress site.

        Args:
            url: WordPress site URL.
            extra_args: Optional extra wpscan flags (e.g. '--enumerate u').
        """
        try:
            binary = resolve_binary("wpscan")
            argv = [binary, "--url", url, *split_extra_args(extra_args)]
            result = await run_argv(argv)
            return result.format()
        except TOOL_EXCEPTION_TYPES as exc:
            return tool_error(exc)
