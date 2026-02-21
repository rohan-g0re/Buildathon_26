"""
Sandbox subgraph — LangGraph subgraph for one policy negotiation.

Flow (boardroom model, 1 Critic + 3 DMs in parallel per round):
  START → critic_respond → all_dms_respond → round_check
      → (if round < max_rounds) → critic_respond → all_dms_respond → (loop)
      → (if round >= max_rounds) → score_move → END

See: docs/architecture/LLD_sandbox.md § 7
"""

from langgraph.graph import StateGraph, START, END
from models.state import SandboxState
from graph.sandbox.critic import critic_respond
from graph.sandbox.decision_maker import all_dms_respond
from graph.sandbox.scoring import score_move


def build_sandbox_subgraph():
    """Builds the sandbox subgraph for one policy negotiation."""
    builder = StateGraph(SandboxState)

    # Nodes
    builder.add_node("critic_respond", critic_respond)
    builder.add_node("all_dms_respond", all_dms_respond)
    builder.add_node("score_move", score_move)

    # Entry: START → critic opening
    builder.add_edge(START, "critic_respond")

    # Critic → all DMs respond in parallel
    builder.add_edge("critic_respond", "all_dms_respond")

    # After all DMs respond: check round count
    def should_continue(state: SandboxState) -> str:
        if state["current_round"] >= state["max_rounds"]:
            return "score_move"
        return "critic_respond"

    builder.add_conditional_edges("all_dms_respond", should_continue)

    # Score → END
    builder.add_edge("score_move", END)

    return builder.compile()


sandbox_subgraph = build_sandbox_subgraph()
