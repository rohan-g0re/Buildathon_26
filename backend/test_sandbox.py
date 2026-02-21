"""
Test for Sandbox (Layer 3+4) — Critic vs Decision Makers negotiation + scoring.
Run from backend/:  python test_sandbox.py

Reads move(s) from backend/output/moves/ and runs the full sandbox subgraph
(bypassing Blaxel). Writes conversation logs and scores to output/sandbox/.

Environment variables:
  TEST_MOVE    — which move to test (default: m3). Set to "all" to run all
                 moves sequentially, skipping blank stubs.
  MAX_ROUNDS   — negotiation rounds (default: 3, production: 10)
  TEST_TICKER  — company ticker (default: AAPL)

Prerequisite: run test_layer_0.py, test_layer_1.py, test_layer_2.py first.
"""

import asyncio
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from graph.sandbox.subgraph import sandbox_subgraph
from graph.sandbox.conversation import format_transcript

# Stubs have ~9 lines (header only). Real moves have 30+.
# Matches MIN_MOVE_CONTENT_LINES in orchestrator.py.
MIN_CONTENT_LINES = 30


def _list_move_files(moves_dir: str) -> list[str]:
    """Return sorted list of move IDs (m1..m15) that exist on disk."""
    ids = []
    for fname in os.listdir(moves_dir):
        match = re.match(r"^(m\d+)\.md$", fname)
        if match:
            ids.append(match.group(1))
    # Sort numerically: m1, m2, ..., m15
    ids.sort(key=lambda x: int(x[1:]))
    return ids


def _is_real_move(filepath: str) -> bool:
    """Check if a move file has real content (not just a header stub)."""
    with open(filepath, "r", encoding="utf-8") as f:
        lines = f.readlines()
    return len(lines) >= MIN_CONTENT_LINES


async def run_single_move(
    move_id: str,
    moves_dir: str,
    output_dir: str,
    max_rounds: int,
    ticker: str,
) -> dict | None:
    """
    Run the sandbox subgraph for one move.
    Returns the final state dict, or None if the move is blank.
    """
    move_path = os.path.join(moves_dir, f"{move_id}.md")

    if not os.path.exists(move_path):
        print(f"  SKIP {move_id}: file not found ({move_path})")
        return None

    if not _is_real_move(move_path):
        print(f"  SKIP {move_id}: blank stub (< {MIN_CONTENT_LINES} lines)")
        return None

    with open(move_path, "r", encoding="utf-8") as f:
        move_content = f.read()

    move_document = {
        "move_id": move_id,
        "content": move_content,
        "ticker": ticker,
    }

    print(f"\n{'='*60}")
    print(f"  SANDBOX: {move_id} ({ticker}) | {max_rounds} rounds")
    print(f"  Agents: 1 Critic + 3 Decision Makers (D1, D2, D3)")
    print(f"{'='*60}")

    # Build fresh state for this move (conversation log starts empty)
    subgraph_input = {
        "move_document": move_document,
        "ticker": ticker,
        "conversation": [],
        "current_round": 0,
        "max_rounds": max_rounds,
        "scores": {},
        "total_score": 0,
        "status_updates": [],
    }

    # Stream the subgraph — collect final state from the stream itself
    # (NO second ainvoke call — that would double LLM costs)
    final_state = dict(subgraph_input)  # start with input, overlay updates

    async for event in sandbox_subgraph.astream(
        subgraph_input, stream_mode="updates"
    ):
        for node_name, node_output in event.items():
            # Merge node output into final_state
            for key, value in node_output.items():
                if key == "status_updates":
                    # status_updates uses the `add` reducer — accumulate
                    final_state.setdefault("status_updates", [])
                    final_state["status_updates"].extend(value)
                else:
                    # All other keys: replace (nodes already build full lists)
                    final_state[key] = value

            # Print progress
            for update in node_output.get("status_updates", []):
                evt = update.get("event", "")
                if evt == "sandbox_round":
                    r = update.get("round", "?")
                    status = update.get("status", "")
                    print(f"  Round {r}: {status}")
                elif evt == "sandbox_scored":
                    score = update.get("score", "?")
                    print(f"  SCORED: {score}/120")

    # ── Write outputs ────────────────────────────────────────
    sandbox_out = os.path.join(output_dir, "sandbox", move_id)
    os.makedirs(sandbox_out, exist_ok=True)

    # Conversation transcript as readable markdown (single shared thread)
    conversation = final_state.get("conversation", [])
    transcript = format_transcript(conversation)
    transcript_path = os.path.join(sandbox_out, "conversation.md")
    with open(transcript_path, "w", encoding="utf-8") as f:
        f.write(
            f"# Negotiation Transcript: Critic vs Decision Makers\n"
        )
        f.write(
            f"**Move:** {move_id} | **Ticker:** {ticker} "
            f"| **Rounds:** {max_rounds}\n\n---\n\n"
        )
        f.write(transcript)
    print(f"  Written: {transcript_path}")

    # Raw conversation logs as JSON
    logs_json_path = os.path.join(sandbox_out, "conversation_logs.json")
    with open(logs_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"conversation": conversation},
            f,
            indent=2,
        )

    # Scores — markdown
    scores = final_state.get("scores", {})
    total = final_state.get("total_score", 0)

    scores_path = os.path.join(sandbox_out, "scores.md")
    with open(scores_path, "w", encoding="utf-8") as f:
        f.write(f"# Scoring Results: {move_id}\n\n")
        f.write(
            f"**Ticker:** {ticker} | **Rounds:** {max_rounds} "
            f"| **Total Score:** {total}/120\n\n---\n\n"
        )
        for dm_id, dm_scores in scores.items():
            dm_total = sum(
                v for k, v in dm_scores.items() if k != "reasoning" and isinstance(v, (int, float))
            )
            reasoning = dm_scores.get("reasoning", "No reasoning provided")
            f.write(f"## {dm_id}\n\n")
            f.write("| Metric | Score |\n")
            f.write("|--------|-------|\n")
            for metric in [
                "impact",
                "feasibility",
                "risk_adjusted_return",
                "strategic_alignment",
            ]:
                f.write(
                    f"| {metric.replace('_', ' ').title()} "
                    f"| {dm_scores.get(metric, '?')}/10 |\n"
                )
            f.write(f"| **Subtotal** | **{dm_total}/40** |\n\n")
            f.write(f"*Reasoning:* {reasoning}\n\n---\n\n")

    # Scores — JSON
    scores_json_path = os.path.join(sandbox_out, "scores.json")
    with open(scores_json_path, "w", encoding="utf-8") as f:
        json.dump(
            {"move_id": move_id, "total_score": total, "scores_by_agent": scores},
            f,
            indent=2,
        )

    print(f"  Scores: {scores_path}")
    print(f"  Total score for {move_id}: {total}/120")

    return final_state


async def main():
    output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "output")
    moves_dir = os.path.join(output_dir, "moves")

    # Config from env
    move_id = os.environ.get("TEST_MOVE", "m3")
    max_rounds = int(os.environ.get("MAX_ROUNDS", "3"))
    ticker = os.environ.get("TEST_TICKER", "AAPL")

    if not os.path.isdir(moves_dir):
        print(f"ERROR: Moves directory not found: {moves_dir}")
        print("Run test_layer_2.py first.")
        return

    # ── ALL_MOVES mode ───────────────────────────────────────
    if move_id.lower() == "all":
        all_ids = _list_move_files(moves_dir)
        print(f"ALL_MOVES mode: found {len(all_ids)} move files")
        print(f"  Rounds per move: {max_rounds}")
        print(f"  Ticker: {ticker}")

        results_summary = []

        for mid in all_ids:
            result = await run_single_move(
                mid, moves_dir, output_dir, max_rounds, ticker
            )
            if result is not None:
                results_summary.append(
                    (mid, result.get("total_score", 0))
                )
            # State is cleared automatically — each call builds fresh input

        # Print summary table
        print(f"\n{'='*60}")
        print("  SUMMARY: All Moves")
        print(f"{'='*60}")
        print(f"  {'Move':<8} {'Score':>10}")
        print(f"  {'-'*8} {'-'*10}")
        for mid, score in sorted(results_summary, key=lambda x: x[1], reverse=True):
            print(f"  {mid:<8} {score:>7}/120")
        print()

    # ── Single move mode ─────────────────────────────────────
    else:
        result = await run_single_move(
            move_id, moves_dir, output_dir, max_rounds, ticker
        )
        if result is None:
            print(f"\nERROR: Could not run sandbox for {move_id}.")
            print("Try a move with real content: TEST_MOVE=m3 python test_sandbox.py")

    print("\nDone.")


if __name__ == "__main__":
    asyncio.run(main())
