"""
Sandbox orchestrator — runs move negotiations concurrently.

Uses astream() per subgraph so that each node's status_updates are
published to SSE in real-time.  Up to ``settings.sandbox_concurrency``
negotiations run in parallel (controlled by asyncio.Semaphore).

When use_blaxel=True, each negotiation runs inside an isolated Blaxel
sandbox.  When use_blaxel=False (default / local dev), the subgraph
runs directly in-process — no Blaxel dependency required.

See: docs/architecture/LLD_sandbox.md § 8
"""

import asyncio
import logging
import time
from typing import Callable, Awaitable, Optional
from models.state import PipelineState, SandboxState
from graph.sandbox.subgraph import sandbox_subgraph
from config.settings import settings

log = logging.getLogger("sandbox")

MIN_MOVE_CONTENT_LINES = 10

# ── Real-time SSE callback ─────────────────────────────────────
_sse_publish: Optional[Callable[[dict], Awaitable[None]]] = None


def set_sse_publish(fn: Optional[Callable[[dict], Awaitable[None]]]):
    """Set the SSE publish callback for the sandbox orchestrator."""
    global _sse_publish
    _sse_publish = fn


async def _publish(event: dict):
    """Publish an SSE event immediately if a callback is registered."""
    if _sse_publish is not None:
        await _sse_publish(event)


def _is_move_substantive(move: dict) -> bool:
    """Check if a move document has real content (not a blank stub)."""
    content = move.get("content", "")
    return len(content.strip().split("\n")) >= MIN_MOVE_CONTENT_LINES


def _deduplicate_moves(moves: list[dict]) -> list[dict]:
    """Remove duplicate move_ids, keeping the first occurrence."""
    seen = set()
    unique = []
    for move in moves:
        mid = move.get("move_id")
        if mid not in seen:
            seen.add(mid)
            unique.append(move)
    return unique


async def _negotiate_move(
    sem: asyncio.Semaphore,
    move: dict,
    idx: int,
    total_moves: int,
    ticker: str,
) -> dict:
    """
    Run a single move negotiation, gated by the semaphore.
    Returns a dict with keys: score, log, status_updates.
    """
    move_id = move["move_id"]

    # ── Content validation: skip blank stubs (no semaphore needed) ──
    if not _is_move_substantive(move):
        content_lines = len(move.get("content", "").strip().split("\n"))
        log.info("(%d/%d) %s: SKIP (blank stub, %d lines < %d min)",
                 idx, total_moves, move_id, content_lines, MIN_MOVE_CONTENT_LINES)
        skip_event = {
            "event": "sandbox_skipped", "move": move_id,
            "reason": "blank_stub",
        }
        await _publish(skip_event)
        return {
            "score": {
                "move_id": move_id,
                "total_score": 0,
                "scores_by_agent": {},
                "skipped": True,
                "reason": f"Move content insufficient for evaluation "
                          f"(< {MIN_MOVE_CONTENT_LINES} lines)",
            },
            "log": None,
            "status_updates": [skip_event],
        }

    async with sem:
        title = move.get("title", "Untitled")[:50]
        content_len = len(move.get("content", ""))
        log.info("(%d/%d) %s: Negotiating — \"%s\" (%d chars)",
                 idx, total_moves, move_id, title, content_len)
        move_start = time.time()

        start_event = {
            "event": "sandbox_move_start",
            "move": move_id,
            "title": move.get("title", "Untitled"),
            "risk_level": move.get("risk_level", "unknown"),
            "persona": move.get("persona", ""),
            "total_moves": total_moves,
            "max_rounds": settings.num_negotiation_rounds,
        }
        await _publish(start_event)
        status_updates_pre: list[dict] = [start_event]

        # ── Optional Blaxel sandbox creation ─────────────────
        sandbox = None
        if settings.use_blaxel:
            from sandbox.blaxel_manager import (
                create_negotiation_sandbox,
                cleanup_sandbox,
            )
            sandbox = await create_negotiation_sandbox(
                ticker=ticker, move_id=move_id,
            )

        subgraph_input: SandboxState = {
            "move_document": move,
            "ticker": ticker,
            "conversation": [],
            "current_round": 0,
            "max_rounds": settings.num_negotiation_rounds,
            "scores": {},
            "total_score": 0,
            "status_updates": [],
        }

        status_updates: list[dict] = list(status_updates_pre)

        try:
            result = {}
            async for event in sandbox_subgraph.astream(
                subgraph_input, stream_mode="updates"
            ):
                for node_name, node_output in event.items():
                    for key, value in node_output.items():
                        if key == "status_updates":
                            result.setdefault("status_updates", [])
                            result["status_updates"].extend(value)
                        elif isinstance(value, list) and isinstance(
                            result.get(key), list
                        ):
                            result[key].extend(value)
                        else:
                            result[key] = value

                    for update in node_output.get("status_updates", []):
                        await _publish(update)
                        status_updates.append(update)

            score = result.get("total_score", 0)
            elapsed = time.time() - move_start
            log.info("(%d/%d) %s: SCORED %d/120 (%.1fs)",
                     idx, total_moves, move_id, score, elapsed)

            return {
                "score": {
                    "move_id": move_id,
                    "total_score": result.get("total_score", 0),
                    "scores_by_agent": result.get("scores", {}),
                },
                "log": {
                    "move_id": move_id,
                    "conversation": result.get("conversation", []),
                },
                "status_updates": status_updates,
            }

        except Exception as e:
            elapsed = time.time() - move_start
            log.error("(%d/%d) %s: FAILED after %.1fs: %s",
                      idx, total_moves, move_id, elapsed, e, exc_info=True)
            error_event = {
                "event": "sandbox_skipped", "move": move_id,
                "reason": f"error: {e}",
            }
            await _publish(error_event)
            status_updates.append(error_event)
            return {
                "score": {
                    "move_id": move_id,
                    "total_score": 0,
                    "scores_by_agent": {},
                    "skipped": True,
                    "reason": f"Sandbox error: {e}",
                },
                "log": None,
                "status_updates": status_updates,
            }

        finally:
            if sandbox is not None:
                from sandbox.blaxel_manager import cleanup_sandbox
                await cleanup_sandbox(sandbox)


async def sandbox_orchestrator(state: PipelineState) -> dict:
    """
    Negotiates all move suggestions concurrently (up to
    settings.sandbox_concurrency at a time).  SSE events stream
    in real-time as each subgraph node completes.
    """
    raw_moves = state["move_suggestions"]
    moves = _deduplicate_moves(raw_moves)
    total_moves = len(moves)

    log.info("Sandbox Orchestrator START: %d unique moves (from %d raw, %d duplicates removed)",
             total_moves, len(raw_moves), len(raw_moves) - total_moves)
    log.info("Rounds per move: %d, Decision makers: %d, Concurrency: %d",
             settings.num_negotiation_rounds, settings.num_decision_makers,
             settings.sandbox_concurrency)

    orchestrator_start = time.time()

    layer_start_event = {"event": "layer_start", "layer": 3}
    await _publish(layer_start_event)

    sem = asyncio.Semaphore(settings.sandbox_concurrency)

    results = await asyncio.gather(*[
        _negotiate_move(sem, move, idx, total_moves, state["company_ticker"])
        for idx, move in enumerate(moves, 1)
    ])

    all_scores = [r["score"] for r in results]
    all_logs = [r["log"] for r in results if r["log"] is not None]
    all_status_updates = [layer_start_event]
    for r in results:
        all_status_updates.extend(r["status_updates"])

    total_elapsed = time.time() - orchestrator_start
    scored_count = sum(1 for s in all_scores if not s.get("skipped"))
    log.info("Sandbox Orchestrator DONE: %d scored, %d skipped, %.1fs total",
             scored_count, total_moves - scored_count, total_elapsed)

    layer_complete_event = {
        "event": "layer_complete", "layer": 3, "status": "done",
        "total_policies_scored": len(all_scores),
    }
    await _publish(layer_complete_event)
    all_status_updates.append(layer_complete_event)

    return {
        "policy_scores": all_scores,
        "conversation_logs": all_logs,
        "status_updates": all_status_updates,
    }
