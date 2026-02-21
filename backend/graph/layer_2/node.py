"""
Layer 2 dispatch node — fans out to 5 parallel analyst agents via Send.

See: docs/architecture/LLD_layer_2.md § 4.1
"""

from langgraph.types import Send
from config.personas import ANALYST_PERSONAS
from config.settings import settings


def dispatch_layer_2(state: dict) -> list[Send]:
    """
    Conditional edge after Layer 1 reduce.
    Dispatches N parallel analyst agents (controlled by NUM_ANALYST_AGENTS in .env).
    Each agent gets F1, F2, and its persona config.
    """
    active_personas = ANALYST_PERSONAS[:settings.num_analyst_agents]
    return [
        Send("analyst_agent", {
            "ticker": state["company_ticker"],
            "f1": state["f1_financial_inference"],
            "f2": state["f2_trend_inference"],
            "persona": persona,
        })
        for persona in active_personas
    ]
