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
    allowed_hosts: tuple[str, ...] = ()
    allowed_origins: tuple[str, ...] = ()
    log_dir: Path = field(default_factory=lambda: Path("logs"))
    log_level: str = "INFO"
    log_max_bytes: int = 5_000_000
    log_backup_count: int = 5


def _truthy(value: str | None, default: bool = False) -> bool:
    if value is None or value.strip() == "":
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv(name: str) -> tuple[str, ...]:
    raw = os.getenv(name, "").strip()
    if not raw:
        return ()
    return tuple(part.strip() for part in raw.split(",") if part.strip())


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
    default_log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir_raw = os.getenv("LOG_DIR", "").strip()
    return Settings(
        host=os.getenv("MCP_HOST", "0.0.0.0"),
        port=int(os.getenv("MCP_PORT", "8000")),
        auth_token=os.getenv("MCP_AUTH_TOKEN", "").strip(),
        allow_raw=_truthy(os.getenv("ALLOW_RAW"), default=False),
        default_timeout=int(os.getenv("DEFAULT_TIMEOUT", "300")),
        binaries=binaries,
        allowed_hosts=_csv("MCP_ALLOWED_HOSTS"),
        allowed_origins=_csv("MCP_ALLOWED_ORIGINS"),
        log_dir=Path(log_dir_raw) if log_dir_raw else default_log_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
        log_max_bytes=int(os.getenv("LOG_MAX_BYTES", "5000000")),
        log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
    )


settings = load_settings()

# Names that may be executed via the structured tool runner (basename match).
ALLOWED_BINARIES: frozenset[str] = frozenset(settings.binaries.keys())
