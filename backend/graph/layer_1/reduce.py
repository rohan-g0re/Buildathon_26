"""
Layer 1 reduce node — collects F1 + F2 into parent state.

See: docs/architecture/LLD_layer_1.md § 4.3
"""

import logging

log = logging.getLogger("layer_1.reduce")


def layer_1_reduce(state: dict) -> dict:
    """
    After both inference agents complete, emits layer_complete event.
    F1 and F2 are already written to state by the agent nodes.
    """
    log.info("Layer 1 REDUCE — both inference agents done, dispatching layer 2")
    return {
        "status_updates": [
            {"event": "layer_complete", "layer": 1, "status": "done",
             "artifacts": ["F1", "F2"]}
        ],
    }
