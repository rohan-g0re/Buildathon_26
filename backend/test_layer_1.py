"""
Quick test for Layer 1 — chunked inference agents.
Run from backend/:  python test_layer_1.py

Reads Layer 0 output from backend/output/ and writes:
  - output/f1_financial_inference.md
  - output/f2_trend_inference.md

Prerequisite: run test_layer_0.py first so the output/ files exist.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.layer_1.financial_inference import financial_inference_agent
from graph.layer_1.trend_inference import trend_inference_agent


async def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    fin_path = os.path.join(output_dir, "financial_data_raw.md")
    news_path = os.path.join(output_dir, "news_data_raw.md")

    if not os.path.exists(fin_path) or not os.path.exists(news_path):
        print("ERROR: Layer 0 output files not found in backend/output/")
        print("Run test_layer_0.py first.")
        return

    with open(fin_path, "r", encoding="utf-8") as f:
        financial_raw = f.read()

    with open(news_path, "r", encoding="utf-8") as f:
        news_raw = f.read()

    ticker = os.environ.get("TEST_TICKER", "AAPL")

    print(f"Running Layer 1 for {ticker}...")
    print(f"  Financial data: {len(financial_raw.splitlines())} lines")
    print(f"  News data: {len(news_raw.splitlines())} lines")

    # Run both agents in parallel (same as LangGraph Send would do)
    fin_result, trend_result = await asyncio.gather(
        financial_inference_agent({
            "agent_type": "financial",
            "raw_data": financial_raw,
            "ticker": ticker,
        }),
        trend_inference_agent({
            "agent_type": "trend",
            "raw_data": news_raw,
            "ticker": ticker,
        }),
    )

    # Write output files
    f1_path = os.path.join(output_dir, "f1_financial_inference.md")
    f2_path = os.path.join(output_dir, "f2_trend_inference.md")

    with open(f1_path, "w", encoding="utf-8") as f:
        f.write(fin_result["f1_financial_inference"])

    with open(f2_path, "w", encoding="utf-8") as f:
        f.write(trend_result["f2_trend_inference"])

    print(f"\nDone. Files written to:")
    print(f"  {f1_path}")
    print(f"  {f2_path}")


if __name__ == "__main__":
    asyncio.run(main())
