"""
Layer 1 dispatch node — fans out to 2 parallel inference agents via Send.

See: docs/architecture/LLD_layer_1.md § 4.1
"""

from langgraph.types import Send


def dispatch_layer_1(state: dict) -> list[Send]:
    """
    Conditional edge after Layer 0.
    Dispatches two parallel inference agents.
    """
    return [
        Send("financial_inference_agent", {
            "agent_type": "financial",
            "raw_data": state["financial_data_raw"],
            "ticker": state["company_ticker"],
        }),
        Send("trend_inference_agent", {
            "agent_type": "trend",
            "raw_data": state["news_data_raw"],
            "ticker": state["company_ticker"],
        }),
    ]
