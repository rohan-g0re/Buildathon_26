"""
LLM client factory — returns a singleton AsyncAnthropic client.

Uses the Anthropic Python SDK directly (no LangChain wrappers).
All agents call through agents/base.py → this module.

See: docs/architecture/LLD_pipeline.md § 9
"""

from anthropic import AsyncAnthropic
from config.settings import settings

_client: AsyncAnthropic | None = None


def get_anthropic_client() -> AsyncAnthropic:
    """
    Returns a singleton AsyncAnthropic client.
    Reuses the same HTTP connection pool across all LLM calls.
    """
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client
