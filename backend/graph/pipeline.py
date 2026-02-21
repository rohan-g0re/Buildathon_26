"""
Main LangGraph StateGraph — parent pipeline definition.

Wires all layers together:
  START → layer_0 → [layer_1 fan-out] → layer_1_reduce
        → [layer_2 fan-out] → layer_2_reduce
        → sandbox_orchestrator → rank_and_output → END

See: docs/architecture/HLD.md § 3
     docs/architecture/LLD_pipeline.md § 2
"""

from langgraph.graph import StateGraph, START, END
from models.state import PipelineState

# Layer 0
from graph.layer_0.node import layer_0_synthesize

# Layer 1
from graph.layer_1.node import dispatch_layer_1
from graph.layer_1.financial_inference import financial_inference_agent
from graph.layer_1.trend_inference import trend_inference_agent
from graph.layer_1.reduce import layer_1_reduce

# Layer 2
from graph.layer_2.node import dispatch_layer_2
from graph.layer_2.analyst_agent import analyst_agent
from graph.layer_2.reduce import layer_2_reduce

# Sandbox (Layer 3 + 4)
from graph.sandbox.orchestrator import sandbox_orchestrator

# Output
from graph.output import rank_and_output


def build_pipeline() -> StateGraph:
    """Assembles and compiles the full agent pipeline."""
    builder = StateGraph(PipelineState)

    # ── NODES ──────────────────────────────────────────
    builder.add_node("layer_0_gather", layer_0_synthesize)
    builder.add_node("financial_inference_agent", financial_inference_agent)
    builder.add_node("trend_inference_agent", trend_inference_agent)
    builder.add_node("layer_1_reduce", layer_1_reduce)
    builder.add_node("analyst_agent", analyst_agent)
    builder.add_node("layer_2_reduce", layer_2_reduce)
    builder.add_node("sandbox_orchestrator", sandbox_orchestrator)
    builder.add_node("rank_and_output", rank_and_output)

    # ── EDGES ──────────────────────────────────────────

    # Entry → Layer 0
    builder.add_edge(START, "layer_0_gather")

    # Layer 0 → Layer 1 (fan-out to 2 parallel inference agents)
    builder.add_conditional_edges("layer_0_gather", dispatch_layer_1)

    # Both inference agents → Layer 1 reduce
    builder.add_edge("financial_inference_agent", "layer_1_reduce")
    builder.add_edge("trend_inference_agent", "layer_1_reduce")

    # Layer 1 reduce → Layer 2 (fan-out to 5 parallel analyst agents)
    builder.add_conditional_edges("layer_1_reduce", dispatch_layer_2)

    # All analyst agents → Layer 2 reduce
    builder.add_edge("analyst_agent", "layer_2_reduce")

    # Layer 2 reduce → Sandbox orchestrator
    builder.add_edge("layer_2_reduce", "sandbox_orchestrator")

    # Sandbox → Rank and output
    builder.add_edge("sandbox_orchestrator", "rank_and_output")

    # Output → END
    builder.add_edge("rank_and_output", END)

    return builder.compile()


pipeline = build_pipeline()
