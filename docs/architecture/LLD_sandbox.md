# Low-Level Design — Sandbox: Layer 3 (Critic) + Layer 4 (Decision Makers)

## 1. Purpose

The sandbox is where move suggestions get **stress-tested through adversarial debate**. A single Critic agent attacks each move's reasoning. Three Decision Maker agents defend it. After 10 rounds of negotiation, the Decision Makers score the move on 4 metrics.

The sandbox runs in an isolated **microVM** — each policy negotiation executes inside an isolated sandbox.

---

## 2. Inputs & Outputs

| | Description |
|---|---|
| **Input** | `move_suggestions: list[dict]` — 15 move documents (m1–m15) from Layer 2 |
| **Output** | `policy_scores: list[dict]` — scores for all 15 moves |
| **Output** | `conversation_logs: list[dict]` — saved i1, i2, i3 per move |

Score dict:
```python
{
    "move_id": "m1",
    "total_score": 98,          # out of 120
    "scores_by_agent": {
        "D1": {"impact": 8, "feasibility": 9, "risk_adjusted_return": 7, "strategic_alignment": 8},  # 32
        "D2": {"impact": 7, "feasibility": 8, "risk_adjusted_return": 8, "strategic_alignment": 9},  # 32
        "D3": {"impact": 9, "feasibility": 8, "risk_adjusted_return": 8, "strategic_alignment": 9},  # 34
    },
    "conversation_logs": {
        "i1": [...],  # full conversation between Critic and D1
        "i2": [...],  # full conversation between Critic and D2
        "i3": [...],  # full conversation between Critic and D3
    }
}
```

---

## 3. Agent Design

### 3.1 Critic Agent (Layer 3)

**Single agent.** Its only job is adversarial probing.

```python
# config/personas.py (Critic persona)

CRITIC_PERSONA = """
You are a veteran CFO who has seen three companies fail from overconfident
strategy. Your job is to find every weakness in a proposed business move.

You are:
- Sharp and intellectually honest — you don't oppose for the sake of opposing
- Thorough — you probe assumptions, demand evidence, and expose logical gaps
- Specific — you cite exact weaknesses, not vague concerns
- Fair — if a point is genuinely strong, you acknowledge it before moving on

When reviewing a move:
1. Identify the strongest claims in the reasoning
2. Challenge each claim: Is the evidence sufficient? Is there a counter-example?
3. Point out risks the proposer may have downplayed
4. Question whether the citations from F1/F2 actually support the conclusion

You are negotiating with decision makers who will defend this move. Engage
with their rebuttals substantively. If they make a good point, acknowledge it.
If they dodge your concern, press harder.
"""
```

### 3.2 Decision Maker Agents (Layer 4)

**Three agents.** All moderately biased toward high-impact decisions but with distinct evaluative lenses.

```python
# config/personas.py (Decision Maker personas)

DECISION_MAKER_PERSONAS = [
    {
        "id": "D1",
        "name": "Growth Strategist",
        "system_prompt": """
You are a Growth Strategist on the board of directors. You evaluate
business moves through the lens of market expansion, competitive
advantage, and long-term positioning.

You are inclined toward high-impact decisions, but you take the critic's
points seriously and must address them substantively before dismissing them.

When defending a move:
- Explain how it drives growth and competitive advantage
- Address the critic's concerns with specific counter-arguments
- Acknowledge valid risks while arguing the upside justifies them
- Reference data from F1/F2 to support your position

You can be swayed by strong market-timing arguments. If the critic
convincingly shows the timing is wrong, you may concede that point.
"""
    },
    {
        "id": "D2",
        "name": "Operational Pragmatist",
        "system_prompt": """
You are an Operational Pragmatist on the board of directors. You evaluate
business moves through the lens of execution feasibility, resource
allocation, and operational risk.

You favor action but respect constraints. You are the person who asks
"can we actually pull this off?" and "what does execution look like?"

When defending a move:
- Explain how the company can realistically execute it
- Address resource and operational concerns raised by the critic
- Propose concrete implementation steps if challenged on feasibility
- Concede if the critic identifies genuine execution blockers

The critic can get to you by pointing out execution gaps, resource
constraints, or operational complexity you haven't addressed.
"""
    },
    {
        "id": "D3",
        "name": "Stakeholder Value Advocate",
        "system_prompt": """
You are a Stakeholder Value Advocate on the board of directors. You evaluate
business moves through the lens of shareholder return, brand impact, and
public perception.

You are biased toward high-visibility wins but sensitive to reputational risk.
You think about how moves will be perceived by investors, media, and customers.

When defending a move:
- Explain the shareholder value proposition
- Address concerns about brand/reputation impact
- Argue for the move's signaling effect to the market
- Concede if the critic shows genuine reputational or regulatory risk

The critic can get to you by pointing out PR disasters, regulatory backlash,
or investor confidence erosion.
"""
    },
]
```

---

## 4. Sandbox Subgraph State

```python
# models/state.py (Sandbox state)

from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class ConversationEntry(TypedDict):
    role: str           # "critic" | "D1" | "D2" | "D3"
    content: str        # the message content
    round: int          # which round this was

class SandboxState(TypedDict):
    # Input
    move_document: dict             # the mx.md move being negotiated
    ticker: str

    # Conversation logs
    i1: list[ConversationEntry]     # Critic ↔ D1 conversation
    i2: list[ConversationEntry]     # Critic ↔ D2 conversation
    i3: list[ConversationEntry]     # Critic ↔ D3 conversation

    # Round tracking
    current_round: int              # 1 through 10
    max_rounds: int                 # 10

    # Scoring (populated after round 10)
    scores: dict                    # {D1: {metric: score}, D2: {...}, D3: {...}}
    total_score: int                # sum out of 120

    # SSE tracking
    status_updates: Annotated[list[dict], add]
```

---

## 5. Negotiation Flow (Round by Round)

### 5.1 Round 1 — Shared Opening

```python
# graph/sandbox/critic.py

import asyncio
from agents.base import call_llm
from config.personas import CRITIC_PERSONA

async def critic_round_1(state: SandboxState) -> dict:
    """
    Round 1: Critic reads the move document and produces ONE set of
    counterpoints. This response is appended to ALL three conversation logs.
    """
    move = state["move_document"]

    prompt = f"""
Here is a proposed business move for {state['ticker']}:

{move['content']}

Provide your initial counterpoints to this move. Challenge the reasoning,
question the evidence, and identify risks.
"""
    response = await call_llm(
        system_prompt=CRITIC_PERSONA,
        user_prompt=prompt,
    )

    entry = {"role": "critic", "content": response, "round": 1}

    return {
        "i1": [entry],  # appended via default (overwrite is fine for round 1)
        "i2": [entry],
        "i3": [entry],
        "current_round": 1,
        "status_updates": [
            {"event": "sandbox_round", "move": move["move_id"],
             "round": 1, "status": "critic_responded"}
        ]
    }
```

### 5.2 Decision Makers Respond (Every Round)

```python
# graph/sandbox/decision_maker.py

import asyncio
from agents.base import call_llm
from config.personas import DECISION_MAKER_PERSONAS

async def dm_respond(state: SandboxState) -> dict:
    """
    All 3 decision makers respond in parallel.
    Each reads their respective conversation log and the original move.
    """
    move = state["move_document"]
    round_num = state["current_round"]

    async def _respond(dm_persona, conversation_log, log_key):
        """Single DM response."""
        transcript = _format_transcript(conversation_log)

        prompt = f"""
You are defending this business move for {state['ticker']}:

{move['content']}

Here is the negotiation transcript so far:
{transcript}

Respond to the critic's latest points. Defend the move where you believe
it has merit, and concede where the critic makes valid points.
"""
        response = await call_llm(
            system_prompt=dm_persona["system_prompt"],
            user_prompt=prompt,
        )

        return log_key, {"role": dm_persona["id"], "content": response, "round": round_num}

    # Run all 3 DM calls in parallel
    tasks = [
        _respond(DECISION_MAKER_PERSONAS[0], state["i1"], "i1"),
        _respond(DECISION_MAKER_PERSONAS[1], state["i2"], "i2"),
        _respond(DECISION_MAKER_PERSONAS[2], state["i3"], "i3"),
    ]
    results = await asyncio.gather(*tasks)

    update = {"status_updates": [
        {"event": "sandbox_round", "move": move["move_id"],
         "round": round_num, "status": "dm_responded"}
    ]}

    for log_key, entry in results:
        update[log_key] = state[log_key] + [entry]

    return update


def _format_transcript(conversation: list[dict]) -> str:
    """Formats conversation log as a readable transcript."""
    lines = []
    for entry in conversation:
        role_label = "CRITIC" if entry["role"] == "critic" else f"DECISION MAKER ({entry['role']})"
        lines.append(f"**[Round {entry['round']}] {role_label}:**\n{entry['content']}\n")
    return "\n---\n".join(lines)
```

### 5.3 Critic Individual Responses (Rounds 2–10)

```python
# graph/sandbox/critic.py (continued)

async def critic_individual(state: SandboxState) -> dict:
    """
    Rounds 2-10: Critic reads each conversation log SEPARATELY and
    generates an INDIVIDUAL response for each DM.
    Three parallel LLM calls.
    """
    move = state["move_document"]
    round_num = state["current_round"] + 1  # incrementing round

    async def _critique(conversation_log, log_key, dm_id):
        transcript = _format_transcript(conversation_log)

        prompt = f"""
You are in round {round_num} of negotiation about this move for {state['ticker']}:

{move['content']}

Your conversation with {dm_id} so far:
{transcript}

Respond to {dm_id}'s latest rebuttal. If they made good points, acknowledge
them. If they dodged your concerns, press harder. Raise new counterpoints
if you see additional weaknesses.
"""
        response = await call_llm(
            system_prompt=CRITIC_PERSONA,
            user_prompt=prompt,
        )

        return log_key, {"role": "critic", "content": response, "round": round_num}

    # 3 parallel critic calls
    tasks = [
        _critique(state["i1"], "i1", "D1 (Growth Strategist)"),
        _critique(state["i2"], "i2", "D2 (Operational Pragmatist)"),
        _critique(state["i3"], "i3", "D3 (Stakeholder Value Advocate)"),
    ]
    results = await asyncio.gather(*tasks)

    update = {
        "current_round": round_num,
        "status_updates": [
            {"event": "sandbox_round", "move": move["move_id"],
             "round": round_num, "status": "critic_responded"}
        ]
    }

    for log_key, entry in results:
        update[log_key] = state[log_key] + [entry]

    return update
```

---

## 6. Scoring System

### 6.1 Scoring Metrics

| Metric | What it measures | Scale |
|--------|-----------------|-------|
| **Impact** | How significant is the effect on growth, revenue, or market position? | 1–10 |
| **Feasibility** | How realistic is execution given current resources and constraints? | 1–10 |
| **Risk-Adjusted Return** | How favorable is the upside relative to the downside? | 1–10 |
| **Strategic Alignment** | How well does the move fit the company's long-term direction? | 1–10 |

Each DM scores out of **40**. Three DMs = out of **120**.

### 6.2 Scoring Node

```python
# graph/sandbox/scoring.py

import asyncio
import json
from agents.base import call_llm
from config.personas import DECISION_MAKER_PERSONAS

SCORING_METRICS = ["impact", "feasibility", "risk_adjusted_return", "strategic_alignment"]

SCORING_PROMPT = """
You have just completed 10 rounds of negotiation about this business move:

{move_content}

Your full negotiation transcript:
{transcript}

Now score this move on the following 4 metrics, each out of 10.
Be OBJECTIVE — reflect what you genuinely believe after the full debate,
not just your initial position. If the critic raised valid concerns that
you could not fully address, let that reflect in your scores.

Metrics:
1. Impact (1-10): How significant is the effect on the company's growth, revenue, or market position?
2. Feasibility (1-10): How realistic is it to execute given current resources, timeline, and constraints?
3. Risk-Adjusted Return (1-10): How favorable is the potential upside relative to the downside exposure?
4. Strategic Alignment (1-10): How well does the move fit the company's long-term direction?

Respond ONLY with valid JSON in this exact format:
{{
    "impact": <int>,
    "feasibility": <int>,
    "risk_adjusted_return": <int>,
    "strategic_alignment": <int>,
    "reasoning": "<1-2 sentence justification for your scores>"
}}
"""

async def score_move(state: SandboxState) -> dict:
    """
    After 10 rounds, each DM scores the move.
    Three parallel scoring calls.
    """
    move = state["move_document"]

    async def _score(dm_persona, conversation_log):
        transcript = _format_transcript(conversation_log)

        prompt = SCORING_PROMPT.format(
            move_content=move["content"],
            transcript=transcript,
        )

        response = await call_llm(
            system_prompt=dm_persona["system_prompt"],
            user_prompt=prompt,
        )

        # Parse JSON response
        try:
            scores = json.loads(response)
        except json.JSONDecodeError:
            # Fallback: extract numbers via regex
            scores = _extract_scores_fallback(response)

        return dm_persona["id"], scores

    tasks = [
        _score(DECISION_MAKER_PERSONAS[0], state["i1"]),
        _score(DECISION_MAKER_PERSONAS[1], state["i2"]),
        _score(DECISION_MAKER_PERSONAS[2], state["i3"]),
    ]
    results = await asyncio.gather(*tasks)

    scores_by_agent = {}
    total = 0
    for dm_id, score_dict in results:
        scores_by_agent[dm_id] = score_dict
        total += sum(score_dict.get(m, 0) for m in SCORING_METRICS)

    return {
        "scores": scores_by_agent,
        "total_score": total,
        "status_updates": [
            {"event": "sandbox_scored", "move": move["move_id"],
             "score": total, "breakdown": scores_by_agent}
        ]
    }
```

---

## 7. Sandbox Subgraph (LangGraph)

```python
# graph/sandbox/subgraph.py

from langgraph.graph import StateGraph, START, END
from models.state import SandboxState
from graph.sandbox.critic import critic_round_1, critic_individual
from graph.sandbox.decision_maker import dm_respond
from graph.sandbox.scoring import score_move

def build_sandbox_subgraph() -> StateGraph:
    """
    Builds the sandbox subgraph for one policy negotiation.

    Flow:
    START → critic_round_1 → dm_respond → round_check
        → (if round < 10) → critic_individual → dm_respond → round_check → (loop)
        → (if round == 10) → score_move → END
    """
    builder = StateGraph(SandboxState)

    # Nodes
    builder.add_node("critic_round_1", critic_round_1)
    builder.add_node("critic_individual", critic_individual)
    builder.add_node("dm_respond", dm_respond)
    builder.add_node("score_move", score_move)

    # Entry
    builder.add_edge(START, "critic_round_1")

    # Round 1: critic → DMs respond
    builder.add_edge("critic_round_1", "dm_respond")

    # After DMs respond: check round count
    def should_continue(state: SandboxState) -> str:
        if state["current_round"] >= state["max_rounds"]:
            return "score_move"
        return "critic_individual"

    builder.add_conditional_edges("dm_respond", should_continue)

    # Rounds 2-10: critic individual → DMs respond → check again
    builder.add_edge("critic_individual", "dm_respond")

    # Score → END
    builder.add_edge("score_move", END)

    return builder.compile()


sandbox_subgraph = build_sandbox_subgraph()
```

---

## 8. Sandbox Orchestrator (Iterates Over 15 Moves)

```python
# graph/sandbox/orchestrator.py

from models.state import PipelineState, SandboxState
from graph.sandbox.subgraph import sandbox_subgraph
from sandbox.sandbox_manager import create_negotiation_sandbox, cleanup_sandbox

async def sandbox_orchestrator(state: PipelineState) -> dict:
    """
    Iterates over all 15 moves sequentially.
    For each move, invokes the sandbox subgraph.
    Collects scores and conversation logs.
    """
    moves = state["move_suggestions"]
    all_scores = []
    all_logs = []
    status_updates = []

    for move in moves:
        # Create sandbox for this negotiation
        sandbox = await create_negotiation_sandbox(
            ticker=state["company_ticker"],
            move_id=move["move_id"]
        )

        # Prepare subgraph input
        subgraph_input: SandboxState = {
            "move_document": move,
            "ticker": state["company_ticker"],
            "i1": [],
            "i2": [],
            "i3": [],
            "current_round": 0,
            "max_rounds": 10,
            "scores": {},
            "total_score": 0,
            "status_updates": [],
        }

        # Invoke sandbox subgraph
        result = await sandbox_subgraph.ainvoke(subgraph_input)

        # Collect results
        all_scores.append({
            "move_id": move["move_id"],
            "total_score": result["total_score"],
            "scores_by_agent": result["scores"],
        })

        all_logs.append({
            "move_id": move["move_id"],
            "i1": result["i1"],
            "i2": result["i2"],
            "i3": result["i3"],
        })

        status_updates.extend(result.get("status_updates", []))

        # Cleanup sandbox
        await cleanup_sandbox(sandbox)

    return {
        "policy_scores": all_scores,
        "conversation_logs": all_logs,
        "status_updates": status_updates + [
            {"event": "layer_complete", "layer": "sandbox", "status": "done",
             "total_policies_scored": len(all_scores)}
        ]
    }
```

---

## 9. Sandbox Integration

```python
# sandbox/sandbox_manager.py

from sandbox_provider.core import SandboxInstance  # your microVM/sandbox provider SDK
from config.settings import settings

async def create_negotiation_sandbox(ticker: str, move_id: str) -> SandboxInstance:
    """
    Creates (or reuses) a sandbox for a single policy negotiation.
    Uses create_if_not_exists to avoid duplicate sandboxes.
    """
    sandbox_name = f"negotiate-{ticker.lower()}-{move_id}"

    sandbox = await SandboxInstance.create_if_not_exists({
        "name": sandbox_name,
        "image": "sandbox/base-image:latest",
        "memory": 2048,
        "labels": {
            "ticker": ticker,
            "move": move_id,
            "layer": "sandbox",
            "project": "ai-consulting-agency",
        },
        "region": settings.sandbox_region,
    })

    return sandbox


async def cleanup_sandbox(sandbox: SandboxInstance):
    """
    Cleans up a sandbox after negotiation completes.
    Deletes the sandbox to free resources.
    """
    try:
        await sandbox.delete()
    except Exception as e:
        # Log but don't fail — sandbox will auto-expire
        import logging
        logging.warning(f"Failed to cleanup sandbox: {e}")


async def save_conversation_to_sandbox(
    sandbox: SandboxInstance,
    log_name: str,
    conversation: list[dict]
):
    """
    Saves a conversation log to the sandbox filesystem.
    Used for persistence and audit trail.
    """
    import json
    content = json.dumps(conversation, indent=2)
    await sandbox.fs.write(f"/workspace/logs/{log_name}.json", content)


async def read_conversation_from_sandbox(
    sandbox: SandboxInstance,
    log_name: str
) -> list[dict]:
    """
    Reads a conversation log from the sandbox filesystem.
    """
    import json
    content = await sandbox.fs.read(f"/workspace/logs/{log_name}.json")
    return json.loads(content)
```

---

## 10. Conversation Log Management

```python
# graph/sandbox/conversation.py

from models.state import ConversationEntry

def append_to_log(
    current_log: list[ConversationEntry],
    role: str,
    content: str,
    round_num: int
) -> list[ConversationEntry]:
    """
    Appends a new entry to a conversation log.
    Returns a NEW list (immutable state update for LangGraph).
    """
    return current_log + [{
        "role": role,
        "content": content,
        "round": round_num,
    }]


def format_transcript(conversation: list[ConversationEntry]) -> str:
    """
    Formats a conversation log as a human-readable transcript.
    This is what gets passed to the LLM on each call.
    """
    lines = []
    for entry in conversation:
        if entry["role"] == "critic":
            role_label = "CRITIC"
        else:
            role_label = f"DECISION MAKER ({entry['role']})"

        lines.append(
            f"**[Round {entry['round']}] {role_label}:**\n"
            f"{entry['content']}"
        )
    return "\n\n---\n\n".join(lines)


def get_latest_message(conversation: list[ConversationEntry]) -> str:
    """Returns the content of the most recent message in the log."""
    if not conversation:
        return ""
    return conversation[-1]["content"]
```

---

## 11. LLM Call Costs (Estimation)

Per policy (1 of 15):
- Round 1: 1 critic call + 3 DM calls = **4 LLM calls**
- Rounds 2-10: (3 critic calls + 3 DM calls) × 9 rounds = **54 LLM calls**
- Scoring: 3 DM scoring calls = **3 LLM calls**
- **Total per policy: ~61 LLM calls**

For all 15 policies: **~915 LLM calls** total in the sandbox layer.

Context window grows with each round (conversation log accumulates). By round 10, each call may include ~8-12K tokens of conversation history. Plan LLM selection accordingly (models with large context windows preferred).

---

## 12. Error Handling

- **LLM call failure during negotiation:** Retry 3 times. If still fails, log the error, record partial conversation, and score with whatever rounds completed.
- **JSON parse failure in scoring:** Fallback regex extractor. If that fails too, assign default score of 5 for each metric (neutral).
- **Sandbox failure:** If sandbox creation fails, fall back to running the negotiation in-process (without isolation). Log a warning.
- **Conversation context overflow:** If conversation log exceeds model's context window, truncate older rounds (keep round 1 + last 3 rounds) and add a summary of truncated rounds.

---

## 13. Testing Strategy

- **Unit test for critic_round_1:** Mock LLM, verify response appended to all 3 logs.
- **Unit test for dm_respond:** Mock LLM, verify 3 parallel responses appended to correct logs.
- **Unit test for scoring:** Mock LLM with known JSON output, verify score aggregation.
- **Integration test for subgraph:** Run full 10-round negotiation with mocked LLM, verify round counting, conversation growth, and final scores.
- **Sandbox integration test:** Create sandbox, write/read files, verify lifecycle (create → use → delete).
