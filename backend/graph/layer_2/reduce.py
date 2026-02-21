"""
Layer 2 reduce node — collects m1–m15 into parent state.

See: docs/architecture/LLD_layer_2.md § 4.3
"""

import logging

log = logging.getLogger("layer_2.reduce")


def layer_2_reduce(state: dict) -> dict:
    """
    After all 5 analyst agents complete, emit layer_complete status.

    NOTE: Do NOT return move_suggestions here. PipelineState uses
    Annotated[list[dict], add] for move_suggestions, so returning
    the full list again would DOUBLE the entries. The moves are
    already correctly accumulated by the add reducer as each
    analyst_agent returns its 3 moves. Sorting happens downstream
    in rank_and_output.
    """
    moves = state.get("move_suggestions", [])
    log.info("Layer 2 REDUCE — %d total moves in state", len(moves))

    return {
        "status_updates": [
            {"event": "layer_complete", "layer": 2, "status": "done",
             "artifacts": [m["move_id"] for m in moves],
             "total_moves": len(moves)}
        ],
    }
