"""
LangGraph state schemas for the entire pipeline.

See: docs/architecture/HLD.md § 4
     docs/architecture/LLD_sandbox.md § 4
"""

from typing import Annotated
from typing_extensions import TypedDict
from operator import add


# ─────────────────────────────────────────────
# Shared types
# ─────────────────────────────────────────────

class ConversationEntry(TypedDict):
    """A single message in a negotiation conversation log."""
    role: str           # "critic" | "D1" | "D2" | "D3"
    content: str        # the message content
    round: int          # which round this was


class MoveSuggestion(TypedDict):
    """A single move suggestion produced by Layer 2."""
    move_id: str                    # m1 through m15
    agent_id: str                   # which analyst produced it
    persona: str                    # persona name
    risk_level: str                 # "low" | "medium" | "high"
    title: str                      # short title of the move
    content: str                    # full markdown with reasoning + citations
    ticker: str


class PolicyScore(TypedDict):
    """Score for a single move after sandbox negotiation."""
    move_id: str
    total_score: int                # out of 120
    scores_by_agent: dict           # {D1: {metric: score}, ...}


# ─────────────────────────────────────────────
# Parent pipeline state
# ─────────────────────────────────────────────

class PipelineState(TypedDict):
    """Top-level state for the LangGraph parent pipeline."""

    # Input
    company_ticker: str

    # Layer 0 output
    financial_data_raw: str
    news_data_raw: str

    # Layer 1 output
    f1_financial_inference: str
    f2_trend_inference: str

    # Layer 2 output
    move_suggestions: Annotated[list[dict], add]

    # Sandbox output
    policy_scores: Annotated[list[dict], add]
    conversation_logs: Annotated[list[dict], add]

    # Final output
    recommended_moves: list[dict]
    other_moves: list[dict]

    # SSE tracking
    status_updates: Annotated[list[dict], add]


# ─────────────────────────────────────────────
# Sandbox subgraph state
# ─────────────────────────────────────────────

class SandboxState(TypedDict):
    """State for the sandbox subgraph (one policy negotiation).

    Uses a single shared conversation log.  Each round has exactly
    1 Critic message + 3 DM messages (all DMs respond in parallel).
    """

    # Input
    move_document: dict
    ticker: str

    # Single shared conversation log (Critic + all 3 DMs per round)
    conversation: list[ConversationEntry]

    # Round tracking
    current_round: int
    max_rounds: int

    # Scoring (populated after final round)
    scores: dict
    total_score: int

    # SSE tracking
    status_updates: Annotated[list[dict], add]
