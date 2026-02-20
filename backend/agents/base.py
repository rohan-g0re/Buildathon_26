"""
Base agent utilities — system prompt + LLM call wrapper with retries.

Uses the Anthropic Python SDK directly via agents/llm.py.
Every agent node in the pipeline calls call_llm() from this module.

See: docs/architecture/LLD_pipeline.md § 9
"""

import asyncio
import logging
import time
from agents.llm import get_anthropic_client
from config.settings import settings

log = logging.getLogger("llm")


async def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    temperature: float | None = None,
    retries: int | None = None,
) -> str:
    """
    Makes a single LLM call with system + user prompt via the Anthropic API.
    Returns the text response.
    Retries on failure with exponential backoff.

    Args:
        system_prompt: The system-level instruction (passed as top-level `system` param).
        user_prompt: The user message content.
        max_tokens: Maximum tokens in the response (required by Anthropic API).
        temperature: Sampling temperature (defaults to settings.llm_temperature).
        retries: Number of retry attempts (defaults to settings.llm_max_retries).
    """
    retries = retries or settings.llm_max_retries
    temperature = temperature if temperature is not None else settings.llm_temperature
    client = get_anthropic_client()

    # Truncate prompt for log display
    prompt_preview = user_prompt[:80].replace("\n", " ") + "..." if len(user_prompt) > 80 else user_prompt.replace("\n", " ")

    for attempt in range(retries):
        try:
            log.info("LLM call (attempt %d/%d) model=%s max_tokens=%d prompt=\"%s\"",
                     attempt + 1, retries, settings.llm_model, max_tokens, prompt_preview)
            start = time.time()

            message = await client.messages.create(
                model=settings.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )

            elapsed = time.time() - start
            text = message.content[0].text
            usage = message.usage
            log.info("LLM done in %.1fs — %d chars, usage: in=%d out=%d",
                     elapsed, len(text), usage.input_tokens, usage.output_tokens)
            return text
        except Exception as e:
            log.warning("LLM call FAILED (attempt %d/%d): %s", attempt + 1, retries, e)
            if attempt == retries - 1:
                log.error("LLM call exhausted all %d retries, raising", retries)
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s
            log.info("LLM retrying in %ds...", wait)
            await asyncio.sleep(wait)
