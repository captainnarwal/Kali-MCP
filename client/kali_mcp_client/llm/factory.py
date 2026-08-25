"""Factory for LLM providers."""

from __future__ import annotations

from kali_mcp_client.config import settings
from kali_mcp_client.llm.anthropic_provider import AnthropicProvider
from kali_mcp_client.llm.base import LLMProvider
from kali_mcp_client.llm.gemini_provider import GeminiProvider
from kali_mcp_client.llm.ollama_provider import OllamaProvider
from kali_mcp_client.llm.openai_provider import OpenAIProvider


def create_provider(name: str | None = None) -> LLMProvider:
    provider = (name or settings.llm_provider).strip().lower()
    if provider == "anthropic":
        return AnthropicProvider()
    if provider == "openai":
        return OpenAIProvider()
    if provider in {"gemini", "google"}:
        return GeminiProvider()
    if provider == "ollama":
        return OllamaProvider()
    raise ValueError(
        f"Unknown LLM_PROVIDER '{provider}'. "
        "Choose: anthropic, openai, gemini, ollama"
    )
