# Low-Level Design — Layer 2: Analyst Agents

## 1. Purpose

Layer 2 performs the work of business analysts. It takes F1 (financial inference) and F2 (trend inference) from Layer 1 and generates **concrete strategic move suggestions** for the company. Each move includes deep reasoning with direct citations from F1 and F2.

---

## 2. Inputs & Outputs

| | Description |
|---|---|
| **Input** | `f1_financial_inference: str` (F1 markdown from Layer 1) |
| **Input** | `f2_trend_inference: str` (F2 markdown from Layer 1) |
| **Output** | `move_suggestions: list[dict]` — 15 move documents (m1–m15) |

Each move dict:
```python
{
    "move_id": "m1",                    # m1 through m15
    "agent_id": "analyst_1",            # which analyst produced it
    "persona": "Conservative Strategist", # persona name
    "risk_level": "low",                # low | medium | high
    "title": "...",                      # short title of the move
    "content": "...",                    # full markdown with reasoning + citations
}
```

---

## 3. Agent Design

### 3.1 Five Analysts, Parallel Execution

Layer 2 has **5 analyst agents** (configurable). Each has a distinct **unbiased** persona — they are analytical lenses, not advocates for any particular risk level. Each produces **3 moves**: low-risk, medium-risk, high-risk.

5 agents × 3 moves = **15 move suggestion documents** (m1.md through m15.md).

All 5 agents run **in parallel** using LangGraph's `Send` API.

### 3.2 Persona Definitions

```python
# config/personas.py (Layer 2 personas)

ANALYST_PERSONAS = [
    {
        "id": "analyst_1",
        "name": "Conservative Strategist",
        "system_prompt": """
You are a conservative business strategist with 20 years of experience
in Fortune 500 companies. You value stability, predictable returns, and
risk mitigation. You analyze through the lens of downside protection
and sustainable growth. You are thorough and methodical in your reasoning.
"""
    },
    {
        "id": "analyst_2",
        "name": "Growth Hacker",
        "system_prompt": """
You are a growth-focused strategist from the tech startup world. You think
in terms of market capture, network effects, and exponential scaling.
You are comfortable with calculated bets and understand that some risk
is necessary for outsized returns. You back your ideas with data.
"""
    },
    {
        "id": "analyst_3",
        "name": "Operations Expert",
        "system_prompt": """
You are a seasoned operations executive who has turned around multiple
companies. You think about efficiency, supply chain, talent management,
and execution capability. You evaluate every move through the lens of
"can we actually do this with our current resources and structure?"
"""
    },
    {
        "id": "analyst_4",
        "name": "Market Contrarian",
        "system_prompt": """
You are a contrarian investor and strategist. You look for what everyone
else is missing. When the market is bullish, you probe for hidden risks.
When it's bearish, you find overlooked opportunities. You thrive on
asymmetric information and unconventional thinking. Always back your
contrarian view with evidence.
"""
    },
    {
        "id": "analyst_5",
        "name": "Stakeholder Diplomat",
        "system_prompt": """
You are a strategist who thinks about all stakeholders: shareholders,
employees, customers, regulators, and the public. You evaluate moves
through the lens of long-term reputation, regulatory risk, ESG impact,
and public perception. You balance profit with responsibility.
"""
    },
]
```

### 3.3 Move Generation Prompt

Each agent receives the same base prompt with F1 + F2, plus their unique persona:

```python
MOVE_GENERATION_PROMPT = """
You are given two inference documents about {ticker}:

## F1 — Financial Inference:
{f1}

## F2 — Market Trend Inference:
{f2}

Based on your analysis of both documents, propose THREE strategic moves
for this company:

1. **Low-Risk Move** — A cautious, defensive move with high probability of
   success and limited downside. Explain why the risk is low.

2. **Medium-Risk Move** — A balanced move with moderate risk and moderate
   potential upside. Explain the risk-reward tradeoff.

3. **High-Risk Move** — A bold, aggressive move with high potential upside
   but significant risk. Explain why the potential reward justifies the risk.

For EACH move, you MUST:
- Give it a clear, descriptive title
- Provide in-depth reasoning (at least 3 paragraphs)
- Directly cite specific data points from F1 and/or F2 that support your reasoning
- Explain potential downsides and how they might be mitigated
- Do NOT produce generic advice. Every sentence should be grounded in the
  specific data provided about this specific company.

Output format (for each move):
---
## [RISK LEVEL] Move: [Title]

### Reasoning
[Your detailed reasoning with citations from F1 and F2]

### Supporting Evidence
- [Citation 1 from F1/F2]
- [Citation 2 from F1/F2]
- ...

### Potential Downsides
[What could go wrong and mitigation strategies]
---
"""
```

---

## 4. LangGraph Implementation

### 4.1 Fan-out using Send

```python
# graph/layer_2/node.py

from langgraph.types import Send
from config.personas import ANALYST_PERSONAS

def dispatch_layer_2(state: dict) -> list[Send]:
    """
    Conditional edge after Layer 1 reduce.
    Dispatches 5 parallel analyst agents via Send.
    Each agent gets F1, F2, and its persona config.
    """
    return [
        Send("analyst_agent", {
            "ticker": state["company_ticker"],
            "f1": state["f1_financial_inference"],
            "f2": state["f2_trend_inference"],
            "persona": persona,
        })
        for persona in ANALYST_PERSONAS
    ]
```

### 4.2 Analyst Agent Node

A single reusable node function. LangGraph invokes it 5 times in parallel with different state (different persona).

```python
# graph/layer_2/analyst_agent.py

import json
from agents.base import call_llm
from config.personas import MOVE_GENERATION_PROMPT

async def analyst_agent(state: dict) -> dict:
    """
    Single analyst agent. Called 5 times in parallel via Send.
    Each invocation has a different persona.
    Produces 3 moves (low, medium, high risk).
    """
    persona = state["persona"]
    ticker = state["ticker"]

    prompt = MOVE_GENERATION_PROMPT.format(
        ticker=ticker,
        f1=state["f1"],
        f2=state["f2"],
    )

    # Call LLM with persona's system prompt
    raw_response = await call_llm(
        system_prompt=persona["system_prompt"],
        user_prompt=prompt,
    )

    # Parse the 3 moves from the response
    moves = _parse_three_moves(raw_response, persona, ticker)

    return {
        "move_suggestions": moves,  # list of 3 dicts, accumulated via add reducer
        "status_updates": [
            {"event": "agent_complete", "layer": 2,
             "agent_id": persona["id"], "persona": persona["name"],
             "move_count": len(moves)}
        ]
    }


def _parse_three_moves(response: str, persona: dict, ticker: str) -> list[dict]:
    """
    Parses the LLM response into 3 structured move dicts.
    Falls back to treating the entire response as a single move if parsing fails.
    """
    risk_levels = ["low", "medium", "high"]
    moves = []

    # Split response by "---" delimiters or "## " headers
    sections = _split_into_sections(response)

    for i, (section, risk) in enumerate(zip(sections[:3], risk_levels)):
        move_id = f"m{_get_global_move_index(persona['id'], i)}"
        moves.append({
            "move_id": move_id,
            "agent_id": persona["id"],
            "persona": persona["name"],
            "risk_level": risk,
            "title": _extract_title(section),
            "content": section.strip(),
            "ticker": ticker,
        })

    return moves


def _get_global_move_index(agent_id: str, local_index: int) -> int:
    """
    Maps (agent_id, local_index) → global move number (1-15).
    analyst_1: m1, m2, m3
    analyst_2: m4, m5, m6
    ...
    analyst_5: m13, m14, m15
    """
    agent_num = int(agent_id.split("_")[1])
    return (agent_num - 1) * 3 + local_index + 1


def _split_into_sections(response: str) -> list[str]:
    """Splits LLM response into sections by --- or ## headers."""
    # Implementation: regex split on '---' or '## ' patterns
    import re
    sections = re.split(r'\n---\n|\n## (?=\[)', response)
    return [s for s in sections if s.strip()]


def _extract_title(section: str) -> str:
    """Extracts the title from a move section header."""
    import re
    match = re.search(r'Move:\s*(.+)', section)
    return match.group(1).strip() if match else "Untitled Move"
```

### 4.3 Reduce Node

```python
# graph/layer_2/reduce.py

def layer_2_reduce(state: dict) -> dict:
    """
    After all 5 analyst agents complete, verify we have 15 moves.
    Sort them by move_id for consistent ordering.
    """
    moves = state.get("move_suggestions", [])

    # Sort by move_id (m1, m2, ... m15)
    moves_sorted = sorted(moves, key=lambda m: int(m["move_id"][1:]))

    return {
        "move_suggestions": moves_sorted,
        "status_updates": [
            {"event": "layer_complete", "layer": 2, "status": "done",
             "artifacts": [m["move_id"] for m in moves_sorted],
             "total_moves": len(moves_sorted)}
        ]
    }
```

---

## 5. LangGraph Wiring

```python
# graph/pipeline.py (Layer 2 section)

from graph.layer_2.node import dispatch_layer_2
from graph.layer_2.analyst_agent import analyst_agent
from graph.layer_2.reduce import layer_2_reduce

# Add nodes
builder.add_node("analyst_agent", analyst_agent)
builder.add_node("layer_2_reduce", layer_2_reduce)

# Layer 1 reduce → fan-out to 5 parallel analysts
builder.add_conditional_edges("layer_1_reduce", dispatch_layer_2)

# All analysts → reduce
builder.add_edge("analyst_agent", "layer_2_reduce")

# Reduce → Sandbox
builder.add_edge("layer_2_reduce", "sandbox_orchestrator")
```

---

## 6. Move Document Output (mx.md)

Each move document looks like:

```markdown
# m7 — [High-Risk] Aggressive International Expansion

**Agent:** Market Contrarian (analyst_4)
**Risk Level:** High
**Company:** AAPL

## Reasoning

[3+ paragraphs of deep reasoning...]

Apple's Q3 revenue decline of 4.2% YoY (F1: Revenue Analysis) combined with
the emerging market sentiment shift noted in Reddit discussions (F2: Social
Sentiment) suggests a window for aggressive international expansion...

## Supporting Evidence
- F1: "Q3 revenue declined 4.2% YoY, driven primarily by domestic market saturation"
- F2: "Reddit r/stocks consensus suggests emerging market demand is underpriced"
- F2: "Polymarket prices 65% probability of India regulatory approval by Q2 2026"

## Potential Downsides
- Currency risk in emerging markets (mitigation: hedging strategy)
- Regulatory uncertainty (mitigation: phased rollout)
- Capital expenditure pressure on near-term margins
```

---

## 7. Error Handling

- If one analyst agent fails, the other 4 should still complete. The reduce node counts moves and logs a warning if fewer than 15.
- If the LLM produces fewer than 3 clearly separated moves, the parser should attempt to extract what it can, and fill missing moves with a "parsing_failed" flag.
- Move IDs are deterministic (based on agent_id + risk_level), so missing moves are identifiable.

---

## 8. Testing Strategy

- **Unit test for analyst_agent:** Mock LLM, verify 3 moves are produced with correct structure.
- **Unit test for _parse_three_moves:** Test with various LLM output formats (well-formatted, edge cases).
- **Integration test:** Feed known F1 + F2 through all 5 agents, verify 15 moves are collected.
- **Parallel execution test:** Verify all 5 agents run concurrently.
