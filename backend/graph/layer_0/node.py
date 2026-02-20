"""
Layer 0 node — synthesizes financial and news data for the target company.

Instead of calling external APIs, this node uses an LLM agent to generate
realistic synthetic data in Markdown format. Two parallel LLM calls produce:
  - financial_data_raw: a ~2-page financial data package
  - news_data_raw: a ~2-page news and sentiment brief

See: docs/architecture/LLD_layer_0.md
"""

import asyncio
import logging
from models.state import PipelineState
from agents.base import call_llm
from config.personas import (
    DATA_SYNTHESIZER_FINANCIAL_PERSONA,
    DATA_SYNTHESIZER_NEWS_PERSONA,
)
from graph.layer_0.templates import FINANCIAL_DATA_TEMPLATE, NEWS_DATA_TEMPLATE

log = logging.getLogger("layer_0")


async def layer_0_synthesize(state: PipelineState) -> dict:
    """
    Layer 0 node: generates synthetic financial and news data via LLM.
    Runs two LLM calls in parallel using asyncio.gather.
    """
    ticker = state["company_ticker"]
    log.info("Layer 0 START — synthesizing data for %s", ticker)
    log.info("  Calling LLM x2 in parallel (financial + news)...")

    financial_prompt = (
        f"Generate a synthetic financial data package for the company "
        f"with ticker {ticker}.\n\n"
        f"Here is an example for a different company (NovaTech Inc., NVTK). "
        f"Follow the EXACT same structure, section headers, and table formats, "
        f"but generate completely new data for {ticker}:\n\n"
        f"{FINANCIAL_DATA_TEMPLATE}"
    )

    news_prompt = (
        f"Generate a synthetic news and sentiment brief for the company "
        f"with ticker {ticker}.\n\n"
        f"Here is an example for a different company (NovaTech Inc., N reduce). "
        f"Follow the EXACT same structure, section headers, and formatting, "
        f"but generate completely new data for {ticker}:\n\n"
        f"{NEWS_DATA_TEMPLATE}"
    )

    financial_raw, news_raw = await asyncio.gather(
        call_llm(
            system_prompt=DATA_SYNTHESIZER_FINANCIAL_PERSONA,
            user_prompt=financial_prompt,
        ),
        call_llm(
            system_prompt=DATA_SYNTHESIZER_NEWS_PERSONA,
            user_prompt=news_prompt,
        ),
    )

    log.info("  Layer 0 DONE — financial=%d chars, news=%d chars",
             len(financial_raw), len(news_raw))

    return {
        "financial_data_raw": financial_raw,
        "news_data_raw": news_raw,
        "status_updates": [
            {"event": "layer_complete", "layer": 0, "status": "done"}
        ],
    }
