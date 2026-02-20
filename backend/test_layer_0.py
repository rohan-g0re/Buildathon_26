"""
Quick test for Layer 0 — synthetic data synthesis.
Run from backend/:  python test_layer_0.py

Outputs two markdown files in backend/output/:
  - financial_data_raw.md
  - news_data_raw.md
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.layer_0.node import layer_0_synthesize


async def main():
    ticker = os.environ.get("TEST_TICKER", "AAPL")
    state = {"company_ticker": ticker}

    print(f"Running Layer 0 for {ticker}...")
    result = await layer_0_synthesize(state)

    # Write output files
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    os.makedirs(output_dir, exist_ok=True)

    fin_path = os.path.join(output_dir, "financial_data_raw.md")
    news_path = os.path.join(output_dir, "news_data_raw.md")

    with open(fin_path, "w", encoding="utf-8") as f:
        f.write(result["financial_data_raw"])

    with open(news_path, "w", encoding="utf-8") as f:
        f.write(result["news_data_raw"])

    print(f"Done. Files written to:")
    print(f"  {fin_path}")
    print(f"  {news_path}")


if __name__ == "__main__":
    asyncio.run(main())
