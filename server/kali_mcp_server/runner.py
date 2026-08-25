"""Safe async subprocess runner with binary allowlist and timeouts."""

from __future__ import annotations

import asyncio
import logging
import shlex
import shutil
from dataclasses import dataclass
from pathlib import Path

from kali_mcp_server.config import ALLOWED_BINARIES, settings

logger = logging.getLogger(__name__)


@dataclass
class CommandResult:
    command: str
    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False

    def format(self) -> str:
        parts = [
            f"command: {self.command}",
            f"returncode: {self.returncode}",
            f"timed_out: {self.timed_out}",
            "--- stdout ---",
            self.stdout.rstrip() or "(empty)",
            "--- stderr ---",
            self.stderr.rstrip() or "(empty)",
        ]
        return "\n".join(parts)


def resolve_binary(name: str) -> str:
    """Resolve a configured tool name to an executable path."""
    configured = settings.binaries.get(name, name)
    path = shutil.which(configured) or (
        configured if Path(configured).is_file() else None
    )
    if path is None:
        raise FileNotFoundError(
            f"Binary '{name}' not found (looked for '{configured}'). "
            "Install it on Kali or set the corresponding *_PATH env var."
        )
    return path


def check_binaries() -> dict[str, bool]:
    """Return presence map for all configured tool binaries."""
    status: dict[str, bool] = {}
    for name, configured in settings.binaries.items():
        found = shutil.which(configured) is not None or Path(configured).is_file()
        status[name] = found
    return status


def _basename_allowed(executable: str) -> bool:
    base = Path(executable).name.lower()
    # Strip common Windows .exe if present; Kali is Linux but be liberal.
    if base.endswith(".exe"):
        base = base[:-4]
    # Allow exact configured basenames (nmap, gobuster, ...)
    allowed_names = {Path(v).name.lower() for v in settings.binaries.values()}
    allowed_names |= {n.lower() for n in ALLOWED_BINARIES}
    return base in allowed_names


async def run_argv(
    argv: list[str],
    *,
    timeout: int | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Run a command as argv list (no shell). First element must be allowlisted."""
    if not argv:
        raise ValueError("Empty command")

    executable = argv[0]
    if not _basename_allowed(executable):
        raise PermissionError(
            f"Binary '{executable}' is not on the allowlist. "
            f"Allowed: {sorted(ALLOWED_BINARIES)}"
        )

    timeout = timeout if timeout is not None else settings.default_timeout
    display = " ".join(shlex.quote(a) for a in argv)
    logger.info("Running: %s (timeout=%ss)", display, timeout)

    try:
        proc = await asyncio.create_subprocess_exec(
            *argv,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=cwd,
        )
    except FileNotFoundError as exc:
        return CommandResult(
            command=display,
            returncode=127,
            stdout="",
            stderr=str(exc),
        )

    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return CommandResult(
            command=display,
            returncode=proc.returncode if proc.returncode is not None else -1,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return CommandResult(
            command=display,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s and was killed.",
            timed_out=True,
        )


async def run_shell(
    command: str,
    *,
    timeout: int | None = None,
    cwd: str | None = None,
) -> CommandResult:
    """Run a raw shell command. Only used by run_command when ALLOW_RAW is set."""
    if not settings.allow_raw:
        raise PermissionError(
            "Raw command execution is disabled. Set ALLOW_RAW=true on the server to enable."
        )
    if not command or not command.strip():
        raise ValueError("Empty command")

    timeout = timeout if timeout is not None else settings.default_timeout
    logger.info("Running shell: %s (timeout=%ss)", command, timeout)

    proc = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    try:
        stdout_b, stderr_b = await asyncio.wait_for(
            proc.communicate(), timeout=timeout
        )
        return CommandResult(
            command=command,
            returncode=proc.returncode if proc.returncode is not None else -1,
            stdout=stdout_b.decode("utf-8", errors="replace"),
            stderr=stderr_b.decode("utf-8", errors="replace"),
        )
    except asyncio.TimeoutError:
        proc.kill()
        await proc.communicate()
        return CommandResult(
            command=command,
            returncode=-1,
            stdout="",
            stderr=f"Command timed out after {timeout}s and was killed.",
            timed_out=True,
        )


def split_extra_args(extra_args: str) -> list[str]:
    """Parse an optional free-form args string with shlex."""
    if not extra_args or not extra_args.strip():
        return []
    return shlex.split(extra_args)
