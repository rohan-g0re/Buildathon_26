"""
Sandbox subgraph — LangGraph subgraph for one policy negotiation.

Flow (single shared conversation, 1 Critic + 1 DM per round):
  START → critic_respond → dm_respond → round_check
      → (if round < max_rounds) → critic_respond → dm_respond → (loop)
      → (if round >= max_rounds) → score_move → END

See: docs/architecture/LLD_sandbox.md § 7
"""

from langgraph.graph import StateGraph, START, END
from models.state import SandboxState
from graph.sandbox.critic import critic_respond
from graph.sandbox.decision_maker import dm_respond
from graph.sandbox.scoring import score_move


def build_sandbox_subgraph():
    """Builds the sandbox subgraph for one policy negotiation."""
    builder = StateGraph(SandboxState)

    # Nodes
    builder.add_node("critic_respond", critic_respond)
    builder.add_node("dm_respond", dm_respond)
    builder.add_node("score_move", score_move)

    # Entry: START → critic opening
    builder.add_edge(START, "critic_respond")

    # Critic → DM responds
    builder.add_edge("critic_respond", "dm_respond")

    # After DM responds: check round count
    def should_continue(state: SandboxState) -> str:
        if state["current_round"] >= state["max_rounds"]:
            return "score_move"
        return "critic_respond"

    builder.add_conditional_edges("dm_respond", should_continue)

    # Score → END
    builder.add_edge("score_move", END)

    return builder.compile()


sandbox_subgraph = build_sandbox_subgraph()
