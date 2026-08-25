"""Environment-driven configuration for the Kali MCP server."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

# Load .env from the server/ directory (parent of this package)
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 8000
    auth_token: str = ""
    allow_raw: bool = False
    default_timeout: int = 300
    binaries: dict[str, str] = field(default_factory=dict)


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def load_settings() -> Settings:
    binaries = {
        "nmap": os.getenv("NMAP_PATH", "nmap"),
        "dirb": os.getenv("DIRB_PATH", "dirb"),
        "gobuster": os.getenv("GOBUSTER_PATH", "gobuster"),
        "nikto": os.getenv("NIKTO_PATH", "nikto"),
        "enum4linux": os.getenv("ENUM4LINUX_PATH", "enum4linux"),
        "wpscan": os.getenv("WPSCAN_PATH", "wpscan"),
        "sqlmap": os.getenv("SQLMAP_PATH", "sqlmap"),
        "hydra": os.getenv("HYDRA_PATH", "hydra"),
        "john": os.getenv("JOHN_PATH", "john"),
        "msfconsole": os.getenv("MSFCONSOLE_PATH", "msfconsole"),
    }
    return Settings(
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        auth_token=os.getenv("MCP_AUTH_TOKEN", "").strip(),
        allow_raw=_truthy(os.getenv("ALLOW_RAW"), default=False),
        default_timeout=int(os.getenv("DEFAULT_TIMEOUT", "300")),
        binaries=binaries,
    )


settings = load_settings()

# Names that may be executed via the structured tool runner (basename match).
ALLOWED_BINARIES: frozenset[str] = frozenset(settings.binaries.keys())
