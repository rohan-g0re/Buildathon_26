"""
Rank and output node — sorts scored policies and splits top 3 vs rest.

See: docs/architecture/LLD_pipeline.md § 3
"""

import logging
from models.state import PipelineState

log = logging.getLogger("output")


def rank_and_output(state: PipelineState) -> dict:
    """
    Takes all 15 scored policies, sorts by total_score descending,
    and splits into top 3 (recommended) and remaining 12 (other).
    """
    scores = state["policy_scores"]
    moves = state["move_suggestions"]

    log.info("Rank & Output START: %d scores, %d moves", len(scores), len(moves))

    # Lookup: move_id → move document
    move_lookup = {m["move_id"]: m for m in moves}

    # Sort scores descending
    ranked = sorted(scores, key=lambda s: s["total_score"], reverse=True)

    # Log the ranking
    for i, entry in enumerate(ranked, 1):
        mid = entry.get("move_id", "?")
        score = entry.get("total_score", 0)
        skipped = entry.get("skipped", False)
        log.info("  #%d  %s  score=%d%s", i, mid, score, " (SKIPPED)" if skipped else "")

    # Attach move document to each score
    for score_entry in ranked:
        score_entry["move_document"] = move_lookup.get(score_entry["move_id"], {})

    # Split top 3 vs rest
    recommended = ranked[:3]
    other = ranked[3:]

    log.info("Rank & Output DONE: top 3 = %s",
             [f"{r['move_id']}({r['total_score']})" for r in recommended])

    return {
        "recommended_moves": recommended,
        "other_moves": other,
        "status_updates": [
            {"event": "pipeline_complete",
             "recommended": [r["move_id"] for r in recommended],
             "other": [o["move_id"] for o in other]}
        ],
    }
