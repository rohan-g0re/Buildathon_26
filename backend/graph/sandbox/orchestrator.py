"""
Sandbox orchestrator — iterates over moves, invokes subgraph per move.

Uses astream() instead of ainvoke() so that each subgraph node's
status_updates are published to SSE *immediately* (real-time),
rather than being batched until the entire orchestrator finishes.

See: docs/architecture/LLD_sandbox.md § 8
"""

import logging
import time
from typing import Callable, Awaitable, Optional
from models.state import PipelineState, SandboxState
from graph.sandbox.subgraph import sandbox_subgraph
from config.settings import settings

log = logging.getLogger("sandbox")

# Moves with fewer than this many lines of content are blank stubs
# and get auto-skipped to avoid wasting LLM calls.
MIN_MOVE_CONTENT_LINES = 10

# ── Real-time SSE callback ─────────────────────────────────────
# Set by _run_pipeline before invoking the LangGraph pipeline.
# The orchestrator calls this to publish events immediately.
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


async def sandbox_orchestrator(state: PipelineState) -> dict:
    """
    Iterates over all move suggestions sequentially.
    For each move, streams the sandbox subgraph so that SSE events
    (sandbox_round, sandbox_scored, etc.) are published in real-time.
    Collects scores and conversation logs.

    Moves with insufficient content are auto-skipped with score 0.
    """
    raw_moves = state["move_suggestions"]

    # Deduplicate (the add reducer can cause duplicates during fan-out)
    moves = _deduplicate_moves(raw_moves)
    total_moves = len(moves)

    log.info("Sandbox Orchestrator START: %d unique moves (from %d raw, %d duplicates removed)",
             total_moves, len(raw_moves), len(raw_moves) - total_moves)
    log.info("Rounds per move: %d, Decision makers: %d",
             settings.num_negotiation_rounds, settings.num_decision_makers)

    all_scores = []
    all_logs = []
    all_status_updates = []
    orchestrator_start = time.time()

    # Publish layer_start immediately
    layer_start_event = {"event": "layer_start", "layer": 3}
    await _publish(layer_start_event)
    all_status_updates.append(layer_start_event)

    for idx, move in enumerate(moves, 1):
        move_id = move["move_id"]

        # ── Content validation: skip blank stubs ─────────────
        if not _is_move_substantive(move):
            content_lines = len(move.get("content", "").strip().split("\n"))
            log.info("(%d/%d) %s: SKIP (blank stub, %d lines < %d min)",
                     idx, total_moves, move_id, content_lines, MIN_MOVE_CONTENT_LINES)
            all_scores.append({
                "move_id": move_id,
                "total_score": 0,
                "scores_by_agent": {},
                "skipped": True,
                "reason": "Move content insufficient for evaluation "
                          f"(< {MIN_MOVE_CONTENT_LINES} lines)",
            })
            skip_event = {
                "event": "sandbox_skipped", "move": move_id,
                "reason": "blank_stub",
            }
            await _publish(skip_event)
            all_status_updates.append(skip_event)
            continue

        # ── Log start ─────────────────────────────────────────
        title = move.get("title", "Untitled")[:50]
        content_len = len(move.get("content", ""))
        log.info("(%d/%d) %s: Negotiating — \"%s\" (%d chars)",
                 idx, total_moves, move_id, title, content_len)
        move_start = time.time()

        # ── Prepare subgraph input (fresh state per move) ────
        subgraph_input: SandboxState = {
            "move_document": move,
            "ticker": state["company_ticker"],
            "conversation": [],
            "current_round": 0,
            "max_rounds": settings.num_negotiation_rounds,
            "scores": {},
            "total_score": 0,
            "status_updates": [],
        }

        try:
            # ── Stream sandbox subgraph for real-time SSE ────────
            result = {}
            async for event in sandbox_subgraph.astream(
                subgraph_input, stream_mode="updates"
            ):
                for node_name, node_output in event.items():
                    # Merge into result
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

                    # Publish status_updates to SSE IMMEDIATELY
                    for update in node_output.get("status_updates", []):
                        await _publish(update)
                        all_status_updates.append(update)

            # ── Log result ────────────────────────────────────────
            score = result.get("total_score", 0)
            elapsed = time.time() - move_start
            log.info("(%d/%d) %s: SCORED %d/120 (%.1fs)",
                     idx, total_moves, move_id, score, elapsed)

            # ── Collect results ──────────────────────────────────
            all_scores.append({
                "move_id": move_id,
                "total_score": result.get("total_score", 0),
                "scores_by_agent": result.get("scores", {}),
            })

            all_logs.append({
                "move_id": move_id,
                "conversation": result.get("conversation", []),
            })

        except Exception as e:
            elapsed = time.time() - move_start
            log.error("(%d/%d) %s: FAILED after %.1fs: %s",
                      idx, total_moves, move_id, elapsed, e, exc_info=True)
            all_scores.append({
                "move_id": move_id,
                "total_score": 0,
                "scores_by_agent": {},
                "skipped": True,
                "reason": f"Sandbox error: {e}",
            })
            error_event = {
                "event": "sandbox_skipped", "move": move_id,
                "reason": f"error: {e}",
            }
            await _publish(error_event)
            all_status_updates.append(error_event)

    total_elapsed = time.time() - orchestrator_start
    scored_count = sum(1 for s in all_scores if not s.get("skipped"))
    log.info("Sandbox Orchestrator DONE: %d scored, %d skipped, %.1fs total",
             scored_count, total_moves - scored_count, total_elapsed)

    # Publish layer_complete immediately
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
