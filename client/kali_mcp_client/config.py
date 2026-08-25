"""Environment-driven configuration for the Kali MCP client / agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(_ENV_PATH)


@dataclass(frozen=True)
class Settings:
    server_url: str
    auth_token: str
    llm_provider: str
    llm_model: str
    anthropic_api_key: str
    openai_api_key: str
    gemini_api_key: str
    mistral_api_key: str
    ollama_host: str
    max_agent_turns: int
    log_dir: Path
    log_level: str
    log_max_bytes: int
    log_backup_count: int


def load_settings() -> Settings:
    gemini_key = (
        os.getenv("GEMINI_API_KEY", "").strip()
        or os.getenv("GOOGLE_API_KEY", "").strip()
    )
    default_log_dir = Path(__file__).resolve().parent.parent / "logs"
    log_dir_raw = os.getenv("LOG_DIR", "").strip()
    return Settings(
        server_url=os.getenv("MCP_SERVER_URL", "http://127.0.0.1:8000/mcp").rstrip(
            "/"
        ),
        auth_token=os.getenv("MCP_AUTH_TOKEN", "").strip(),
        llm_provider=os.getenv("LLM_PROVIDER", "anthropic").strip().lower(),
        llm_model=os.getenv("LLM_MODEL", "claude-sonnet-4-20250514").strip(),
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        openai_api_key=os.getenv("OPENAI_API_KEY", "").strip(),
        gemini_api_key=gemini_key,
        mistral_api_key=os.getenv("MISTRAL_API_KEY", "").strip(),
        ollama_host=os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434").strip(),
        max_agent_turns=int(os.getenv("MAX_AGENT_TURNS", "20")),
        log_dir=Path(log_dir_raw) if log_dir_raw else default_log_dir,
        log_level=os.getenv("LOG_LEVEL", "INFO").strip() or "INFO",
        log_max_bytes=int(os.getenv("LOG_MAX_BYTES", "5000000")),
        log_backup_count=int(os.getenv("LOG_BACKUP_COUNT", "5")),
    )


settings = load_settings()
