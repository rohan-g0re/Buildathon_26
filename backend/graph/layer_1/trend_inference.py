"""
Trend inference agent — produces F2 (Trend Inference Markdown).

Splits the raw news/sentiment data into ~20-line chunks, processes pairs of
chunks in parallel, and appends all short inferences to build F2.

See: docs/architecture/LLD_layer_1.md
"""

import asyncio
import logging
from agents.base import call_llm
from agents.chunker import split_into_chunks
from config.personas import TREND_CHUNK_INFERENCE_PERSONA

log = logging.getLogger("layer_1.trend")


async def _infer_chunk(ticker: str, chunk: str, chunk_index: int) -> str:
    """Generates a short inference for a single chunk of news/sentiment data."""
    prompt = (
        f"Here is section {chunk_index + 1} of the news and sentiment data "
        f"for {ticker}. Provide a concise inference (3-5 sentences) analyzing "
        f"what this section reveals:\n\n{chunk}"
    )
    return await call_llm(
        system_prompt=TREND_CHUNK_INFERENCE_PERSONA,
        user_prompt=prompt,
        max_tokens=512,
    )


async def trend_inference_agent(state: dict) -> dict:
    """
    Produces F2: Trend Inference Markdown.
    Called via Send from dispatch_layer_1.

    Strategy:
    1. Split raw_data into ~20-line chunks
    2. Process chunks in pairs (2 at a time via asyncio.gather)
    3. Append all inferences in order with section separators
    """
    ticker = state["ticker"]
    raw_data = state["raw_data"]

    chunks = split_into_chunks(raw_data, chunk_size=20)
    log.info("Trend inference START — %d chunks from %d chars", len(chunks), len(raw_data))
    inferences: list[str] = []

    # Process chunks in pairs — 2 parallel LLM calls at a time
    for i in range(0, len(chunks), 2):
        tasks = [_infer_chunk(ticker, chunks[i], i)]
        if i + 1 < len(chunks):
            tasks.append(_infer_chunk(ticker, chunks[i + 1], i + 1))

        results = await asyncio.gather(*tasks)
        inferences.extend(results)
        processed = min(i + 2, len(chunks))
        log.info("  Chunk pair %d done (%d/%d chunks processed)", (i // 2) + 1, processed, len(chunks))

    # Assemble F2 document
    header = f"# Market Trend Inference — {ticker}\n"
    body = "\n\n---\n\n".join(inferences)
    f2 = f"{header}\n{body}\n"

    log.info("Trend inference DONE — F2=%d chars", len(f2))

    return {
        "f2_trend_inference": f2,
        "status_updates": [
            {"event": "agent_complete", "layer": 1,
             "agent_id": "trend_inference", "output": "F2"}
        ],
    }
