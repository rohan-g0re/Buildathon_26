"""
Quick test for Layer 2 — 5 analyst agents producing 15 move documents.
Run from backend/:  python test_layer_2.py

Reads Layer 1 output from backend/output/ and writes:
  - output/moves/m1.md through m15.md  (one file per move)
  - output/moves/_summary.md           (index of all moves)

Prerequisite: run test_layer_0.py and test_layer_1.py first.
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config.personas import ANALYST_PERSONAS
from config.settings import settings
from graph.layer_2.analyst_agent import analyst_agent


async def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")

    f1_path = os.path.join(output_dir, "f1_financial_inference.md")
    f2_path = os.path.join(output_dir, "f2_trend_inference.md")

    if not os.path.exists(f1_path) or not os.path.exists(f2_path):
        print("ERROR: Layer 1 output files not found in backend/output/")
        print("Run test_layer_0.py and test_layer_1.py first.")
        return

    with open(f1_path, "r", encoding="utf-8") as f:
        f1 = f.read()

    with open(f2_path, "r", encoding="utf-8") as f:
        f2 = f.read()

    ticker = os.environ.get("TEST_TICKER", "AAPL")

    print(f"Running Layer 2 for {ticker}...")
    print(f"  F1: {len(f1.splitlines())} lines")
    print(f"  F2: {len(f2.splitlines())} lines")
    active_personas = ANALYST_PERSONAS[:settings.num_analyst_agents]
    print(f"  Analysts: {len(active_personas)} (of {len(ANALYST_PERSONAS)} available)")
    print()

    # Run N analyst agents in parallel (controlled by NUM_ANALYST_AGENTS in .env)
    tasks = [
        analyst_agent({
            "ticker": ticker,
            "f1": f1,
            "f2": f2,
            "persona": persona,
        })
        for persona in active_personas
    ]

    results = await asyncio.gather(*tasks)

    # Collect all moves
    all_moves = []
    for result in results:
        moves = result["move_suggestions"]
        status = result["status_updates"][0]
        print(f"  {status['persona']}: {status['move_count']} moves")
        all_moves.extend(moves)

    # Sort by move_id
    all_moves.sort(key=lambda m: int(m["move_id"][1:]))

    # Write individual move files
    moves_dir = os.path.join(output_dir, "moves")
    os.makedirs(moves_dir, exist_ok=True)

    for move in all_moves:
        move_path = os.path.join(moves_dir, f"{move['move_id']}.md")
        header = (
            f"# {move['move_id']} — [{move['risk_level'].upper()}] {move['title']}\n\n"
            f"**Agent:** {move['persona']} ({move['agent_id']})\n"
            f"**Risk Level:** {move['risk_level'].capitalize()}\n"
            f"**Company:** {move['ticker']}\n\n---\n\n"
        )
        with open(move_path, "w", encoding="utf-8") as f:
            f.write(header + move["content"])

    # Write summary index
    summary_path = os.path.join(moves_dir, "_summary.md")
    with open(summary_path, "w", encoding="utf-8") as f:
        f.write(f"# Layer 2 — Move Suggestions for {ticker}\n\n")
        f.write(f"Total moves: {len(all_moves)}\n\n")
        f.write("| Move | Risk | Title | Agent |\n")
        f.write("|------|------|-------|-------|\n")
        for move in all_moves:
            f.write(
                f"| {move['move_id']} | {move['risk_level']} | "
                f"{move['title']} | {move['persona']} |\n"
            )

    print(f"\nDone. {len(all_moves)} moves written to:")
    print(f"  {moves_dir}/m1.md through m{len(all_moves)}.md")
    print(f"  {moves_dir}/_summary.md")


if __name__ == "__main__":
    asyncio.run(main())
