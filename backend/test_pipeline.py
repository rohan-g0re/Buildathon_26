"""
End-to-end pipeline test — Layer 0 through final scored rankings.

Calls each layer's functions directly (no LangGraph StateGraph at the
pipeline level). Intermediate documents are written to disk after each
layer completes, so you can watch progress in real time.

Run from backend/:
  python test_pipeline.py

Environment variables (set in .env):
  TEST_TICKER              — company ticker (default: AAPL)
  NUM_NEGOTIATION_ROUNDS   — rounds per negotiation (default: 3)
  NUM_ANALYST_AGENTS       — how many Layer 2 analysts (default: 5)

Outputs are saved to:  output/pipeline/<ticker>/
"""

import asyncio
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ── Imports (agent functions + settings) ─────────────────────

from config.settings import settings
from config.personas import ANALYST_PERSONAS

# Layer 0
from graph.layer_0.node import layer_0_synthesize

# Layer 1
from graph.layer_1.financial_inference import financial_inference_agent
from graph.layer_1.trend_inference import trend_inference_agent

# Layer 2
from graph.layer_2.analyst_agent import analyst_agent

# Sandbox (Layer 3 + 4) — only the compiled subgraph, not the orchestrator
from graph.sandbox.subgraph import sandbox_subgraph
from graph.sandbox.conversation import format_transcript


# ── Helpers ──────────────────────────────────────────────────

MIN_MOVE_CONTENT_LINES = 10


def _save(path: str, content: str):
    """Write content to a file, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)


def _save_json(path: str, data):
    """Write JSON to a file, creating parent dirs as needed."""
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def _is_move_substantive(move: dict) -> bool:
    """Check if a move has real content (not a blank stub)."""
    content = move.get("content", "")
    return len(content.strip().split("\n")) >= MIN_MOVE_CONTENT_LINES


def _deduplicate_moves(moves: list[dict]) -> list[dict]:
    """Remove duplicate move_ids, keeping first occurrence."""
    seen = set()
    unique = []
    for move in moves:
        mid = move.get("move_id")
        if mid not in seen:
            seen.add(mid)
            unique.append(move)
    return unique


# ── Main pipeline ────────────────────────────────────────────

async def main():
    ticker = os.environ.get("TEST_TICKER", "AAPL")
    num_rounds = settings.num_negotiation_rounds
    num_analysts = settings.num_analyst_agents
    base_dir = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "output", "pipeline", ticker,
    )

    print(f"\n{'='*65}")
    print(f"  END-TO-END PIPELINE")
    print(f"  Ticker:     {ticker}")
    print(f"  Analysts:   {num_analysts}")
    print(f"  Rounds:     {num_rounds}")
    print(f"  Output:     {base_dir}/")
    print(f"{'='*65}")

    pipeline_start = time.time()

    # ══════════════════════════════════════════════════════════
    #  LAYER 0 — Synthetic Data Generation
    # ══════════════════════════════════════════════════════════
    print(f"\n--- Layer 0: Synthesizing data for {ticker} ---")
    t0 = time.time()

    layer_0_result = await layer_0_synthesize({"company_ticker": ticker})
    financial_raw = layer_0_result["financial_data_raw"]
    news_raw = layer_0_result["news_data_raw"]

    _save(os.path.join(base_dir, "financial_data_raw.md"), financial_raw)
    _save(os.path.join(base_dir, "news_data_raw.md"), news_raw)

    print(f"  financial_data_raw.md ({len(financial_raw.splitlines())} lines)")
    print(f"  news_data_raw.md ({len(news_raw.splitlines())} lines)")
    print(f"  Layer 0 done in {time.time() - t0:.1f}s")

    # ══════════════════════════════════════════════════════════
    #  LAYER 1 — Inference Agents (parallel)
    # ══════════════════════════════════════════════════════════
    print(f"\n--- Layer 1: Running inference agents ---")
    t1 = time.time()

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

    f1 = fin_result["f1_financial_inference"]
    f2 = trend_result["f2_trend_inference"]

    _save(os.path.join(base_dir, "f1_financial_inference.md"), f1)
    _save(os.path.join(base_dir, "f2_trend_inference.md"), f2)

    print(f"  f1_financial_inference.md ({len(f1.splitlines())} lines)")
    print(f"  f2_trend_inference.md ({len(f2.splitlines())} lines)")
    print(f"  Layer 1 done in {time.time() - t1:.1f}s")

    # ══════════════════════════════════════════════════════════
    #  LAYER 2 — Analyst Agents (parallel)
    # ══════════════════════════════════════════════════════════
    active_personas = ANALYST_PERSONAS[:num_analysts]
    print(f"\n--- Layer 2: Running {len(active_personas)} analyst agents ---")
    t2 = time.time()

    analyst_tasks = [
        analyst_agent({
            "ticker": ticker,
            "f1": f1,
            "f2": f2,
            "persona": persona,
        })
        for persona in active_personas
    ]
    analyst_results = await asyncio.gather(*analyst_tasks)

    # Collect all moves
    all_moves = []
    for result in analyst_results:
        moves = result["move_suggestions"]
        status = result["status_updates"][0]
        print(f"  {status['persona']}: {status['move_count']} moves")
        all_moves.extend(moves)

    all_moves.sort(key=lambda m: int(m["move_id"][1:]))

    # Write move files immediately
    moves_dir = os.path.join(base_dir, "moves")
    for move in all_moves:
        mid = move["move_id"]
        header = (
            f"# {mid} — [{move['risk_level'].upper()}] {move['title']}\n\n"
            f"**Agent:** {move['persona']} ({move['agent_id']})\n"
            f"**Risk Level:** {move['risk_level'].capitalize()}\n"
            f"**Company:** {ticker}\n\n---\n\n"
        )
        _save(os.path.join(moves_dir, f"{mid}.md"), header + move["content"])

    print(f"  {len(all_moves)} moves written to {moves_dir}/")
    print(f"  Layer 2 done in {time.time() - t2:.1f}s")

    # ══════════════════════════════════════════════════════════
    #  SANDBOX (Layer 3 + 4) — Negotiations + Scoring
    # ══════════════════════════════════════════════════════════
    moves = _deduplicate_moves(all_moves)
    substantive = [m for m in moves if _is_move_substantive(m)]
    skipped = [m for m in moves if not _is_move_substantive(m)]

    print(f"\n--- Sandbox: {len(substantive)} moves to negotiate, "
          f"{len(skipped)} skipped (blank stubs) ---")
    ts = time.time()

    all_scores = []
    all_logs = []

    for skip in skipped:
        mid = skip["move_id"]
        print(f"  {mid}: SKIP (blank stub)")
        sandbox_dir = os.path.join(base_dir, "sandbox", mid)
        _save(os.path.join(sandbox_dir, "SKIPPED.txt"), "Blank stub — insufficient content")
        all_scores.append({
            "move_id": mid, "total_score": 0,
            "scores_by_agent": {}, "skipped": True,
        })

    for idx, move in enumerate(substantive, 1):
        mid = move["move_id"]
        title = move.get("title", "Untitled")[:50]
        print(f"  ({idx}/{len(substantive)}) {mid}: Negotiating — {title}")
        move_start = time.time()

        # Fresh state per move (conversation log starts empty)
        subgraph_input = {
            "move_document": move,
            "ticker": ticker,
            "conversation": [],
            "current_round": 0,
            "max_rounds": num_rounds,
            "scores": {},
            "total_score": 0,
            "status_updates": [],
        }

        result = await sandbox_subgraph.ainvoke(subgraph_input)

        score = result.get("total_score", 0)
        elapsed_move = time.time() - move_start
        print(f"  ({idx}/{len(substantive)}) {mid}: SCORED {score}/120 ({elapsed_move:.1f}s)")

        # Write conversation logs + scores immediately
        sandbox_dir = os.path.join(base_dir, "sandbox", mid)

        # Conversation transcript (single shared thread)
        conversation = result.get("conversation", [])
        transcript = format_transcript(conversation)
        _save(
            os.path.join(sandbox_dir, "conversation.md"),
            f"# Negotiation: Critic vs Decision Makers\n"
            f"**Move:** {mid} | **Ticker:** {ticker} "
            f"| **Rounds:** {num_rounds}\n\n---\n\n"
            + transcript,
        )

        # Raw JSON logs
        _save_json(
            os.path.join(sandbox_dir, "conversation_logs.json"),
            {"conversation": conversation},
        )

        # Scores
        agent_scores = result.get("scores", {})
        scores_md = f"# Scoring Results: {mid}\n\n"
        scores_md += (
            f"**Ticker:** {ticker} | **Rounds:** {num_rounds} "
            f"| **Total Score:** {score}/120\n\n---\n\n"
        )
        for dm_id, dm_scores in agent_scores.items():
            dm_total = sum(
                v for k, v in dm_scores.items()
                if k != "reasoning" and isinstance(v, (int, float))
            )
            reasoning = dm_scores.get("reasoning", "No reasoning provided")
            scores_md += f"## {dm_id}\n\n"
            scores_md += "| Metric | Score |\n|--------|-------|\n"
            for metric in ["impact", "feasibility", "risk_adjusted_return", "strategic_alignment"]:
                scores_md += (
                    f"| {metric.replace('_', ' ').title()} "
                    f"| {dm_scores.get(metric, '?')}/10 |\n"
                )
            scores_md += f"| **Subtotal** | **{dm_total}/40** |\n\n"
            scores_md += f"*Reasoning:* {reasoning}\n\n---\n\n"

        _save(os.path.join(sandbox_dir, "scores.md"), scores_md)
        _save_json(os.path.join(sandbox_dir, "scores.json"), {
            "move_id": mid, "total_score": score, "scores_by_agent": agent_scores,
        })

        all_scores.append({
            "move_id": mid, "total_score": score, "scores_by_agent": agent_scores,
        })
        all_logs.append({
            "move_id": mid, "conversation": result.get("conversation", []),
        })

    print(f"  Sandbox done in {time.time() - ts:.1f}s")

    # ══════════════════════════════════════════════════════════
    #  RANK & OUTPUT
    # ══════════════════════════════════════════════════════════
    print(f"\n--- Final Rankings ---")

    # Build move lookup
    move_lookup = {m["move_id"]: m for m in moves}

    # Sort scores descending
    ranked = sorted(all_scores, key=lambda s: s.get("total_score", 0), reverse=True)

    # Attach move documents
    for entry in ranked:
        entry["move_document"] = move_lookup.get(entry["move_id"], {})

    recommended = ranked[:3]
    other = ranked[3:]

    # Write rankings
    rankings_md = f"# Final Rankings — {ticker}\n\n"
    rankings_md += f"**Analysts:** {num_analysts} | **Rounds:** {num_rounds}\n\n"

    rankings_md += "## Top 3 Recommended Moves\n\n"
    rankings_md += "| Rank | Move | Score | Title |\n"
    rankings_md += "|------|------|-------|-------|\n"
    for i, entry in enumerate(recommended, 1):
        mid = entry.get("move_id", "?")
        sc = entry.get("total_score", 0)
        title = entry.get("move_document", {}).get("title", "Untitled")
        rankings_md += f"| {i} | {mid} | {sc}/120 | {title} |\n"

    rankings_md += "\n## Other Moves\n\n"
    rankings_md += "| Rank | Move | Score | Title |\n"
    rankings_md += "|------|------|-------|-------|\n"
    for i, entry in enumerate(other, len(recommended) + 1):
        mid = entry.get("move_id", "?")
        sc = entry.get("total_score", 0)
        title = entry.get("move_document", {}).get("title", "Untitled")
        skipped_flag = " (skipped)" if entry.get("skipped") else ""
        rankings_md += f"| {i} | {mid} | {sc}/120 | {title}{skipped_flag} |\n"

    _save(os.path.join(base_dir, "final_rankings.md"), rankings_md)
    _save_json(os.path.join(base_dir, "final_rankings.json"), {
        "ticker": ticker,
        "recommended": recommended,
        "other": other,
    })

    # ── Summary table ────────────────────────────────────────
    total_elapsed = time.time() - pipeline_start

    print(f"\n{'='*65}")
    print(f"  FINAL RANKINGS — {ticker}")
    print(f"{'='*65}")
    print(f"  {'Rank':<6} {'Move':<8} {'Score':>10}  Title")
    print(f"  {'-'*6} {'-'*8} {'-'*10}  {'-'*30}")
    for i, entry in enumerate(ranked, 1):
        mid = entry.get("move_id", "?")
        sc = entry.get("total_score", 0)
        title = entry.get("move_document", {}).get("title", "Untitled")[:40]
        marker = " <-- RECOMMENDED" if i <= 3 else ""
        skipped_flag = " (skipped)" if entry.get("skipped") else ""
        print(f"  {i:<6} {mid:<8} {sc:>7}/120  {title}{skipped_flag}{marker}")

    print(f"\n  Total time: {total_elapsed:.1f}s")
    print(f"  All outputs: {base_dir}/")
    print()


if __name__ == "__main__":
    asyncio.run(main())
