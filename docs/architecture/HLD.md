# High-Level Design (HLD)

## 1. System Overview

The system is an AI-powered strategic consulting engine. A user provides a **publicly listed company ticker**. The system collects data, derives inferences, generates strategic moves, stress-tests them through adversarial debate, scores them, and returns ranked recommendations.

The backend is a **LangGraph pipeline** wrapped in **FastAPI**. The frontend is a **NextJS** app that receives real-time progress via **SSE**. Agent sandboxing (Layer 3+4 negotiation) runs in isolated **microVM sandboxes**.

---

## 2. Architecture Diagram (Conceptual)

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FRONTEND (NextJS)                           │
│  ┌──────────┐   ┌──────────────────────────────┐   ┌────────────┐  │
│  │  Ticker   │──▶│   Pipeline Visualization     │──▶│  Results   │  │
│  │  Input    │   │   (zoom-in/out per layer)     │   │  Display   │  │
│  └──────────┘   └──────────────────────────────┘   └────────────┘  │
│                          ▲ SSE (real-time)                          │
└──────────────────────────┼──────────────────────────────────────────┘
                           │
┌──────────────────────────┼──────────────────────────────────────────┐
│                    BACKEND (FastAPI + LangGraph)                     │
│                          │                                          │
│  ┌───────────────────────┼────────────────────────────────────┐     │
│  │              LangGraph Parent Pipeline                      │     │
│  │                                                             │     │
│  │  ┌─────────┐   ┌─────────┐   ┌─────────┐   ┌───────────┐ │     │
│  │  │ Layer 0 │──▶│ Layer 1 │──▶│ Layer 2 │──▶│  Sandbox  │ │     │
│  │  │ Gather  │   │ Infer   │   │ Analyze │   │  (L3+L4)  │ │     │
│  │  │         │   │ ║ ║     │   │ ║║║║║   │   │  Sandbox  │ │     │
│  │  └─────────┘   └─────────┘   └─────────┘   └───────────┘ │     │
│  │       │              │              │              │        │     │
│  │       ▼              ▼              ▼              ▼        │     │
│  │   synthetic     F1 + F2       m1 – m15       scores +     │     │
│  │   (markdown)   (markdown)    (markdown)    conversation    │     │
│  │                                               logs         │     │
│  └────────────────────────────────────────────────────────────┘     │
│                                                                     │
│  ┌──────────────────┐  ┌───────────────────┐                       │
│  │  SSE Manager     │  │  Sandbox Manager  │                       │
│  │  (status events) │  │  (sandbox lifecycle│                       │
│  └──────────────────┘  └───────────────────┘                       │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 3. LangGraph Pipeline Topology

The entire system is one compiled `StateGraph`. Layers are represented as nodes (or subgraphs). Edges between layers are sequential. Parallelism happens **within** layers using LangGraph's `Send` API.

```
START
  │
  ▼
[layer_0_gather]          ── single node, 2 parallel LLM calls (synthesizer)
  │
  ▼
[layer_1_dispatch]        ── conditional edge returns 2x Send (parallel)
  ║         ║
  ▼         ▼
[inference_agent]  x2     ── fan-out: financial + trend (parallel)
  ║         ║
  ▼         ▼
[layer_1_reduce]          ── collects F1, F2 into parent state
  │
  ▼
[layer_2_dispatch]        ── conditional edge returns 5x Send (parallel)
  ║ ║ ║ ║ ║
  ▼ ▼ ▼ ▼ ▼
[analyst_agent]  x5       ── fan-out: 5 personas, each returns 3 moves
  ║ ║ ║ ║ ║
  ▼ ▼ ▼ ▼ ▼
[layer_2_reduce]          ── collects m1–m15 into parent state
  │
  ▼
[sandbox_orchestrator]    ── iterates over 15 moves sequentially
  │                           invokes sandbox subgraph per move
  │   ┌─────────────────────────────────────────────┐
  │   │  SANDBOX SUBGRAPH (per move, in sandbox)    │
  │   │                                             │
  │   │  [critic_round_1] ── writes to i1,i2,i3    │
  │   │       │                                     │
  │   │       ▼                                     │
  │   │  [dm_respond]  ── 3 parallel LLM calls      │
  │   │       │                                     │
  │   │       ▼                                     │
  │   │  ◆ round < 10?                             │
  │   │  YES ──▶ [critic_individual] ── 3 parallel  │
  │   │              │                              │
  │   │              ▼                              │
  │   │         [dm_respond] ── 3 parallel          │
  │   │              │                              │
  │   │              ▼                              │
  │   │         ◆ round < 10? ──YES──▶ (loop)      │
  │   │                         NO                  │
  │   │                          │                  │
  │   │                          ▼                  │
  │   │                    [score_move]             │
  │   │                          │                  │
  │   │                         END                 │
  │   └─────────────────────────────────────────────┘
  │
  ▼
[rank_and_output]         ── sorts by score, picks top 3
  │
  ▼
 END
```

---

## 4. State Schema (Top-Level)

```python
from typing import Annotated
from typing_extensions import TypedDict
from operator import add

class PipelineState(TypedDict):
    # Input
    company_ticker: str

    # Layer 0 output
    financial_data_raw: str          # synthetic financial data (markdown)
    news_data_raw: str               # synthetic news/sentiment data (markdown)

    # Layer 1 output
    f1_financial_inference: str      # F1 markdown
    f2_trend_inference: str          # F2 markdown

    # Layer 2 output
    move_suggestions: Annotated[list[dict], add]  # m1–m15 (accumulated via reducer)

    # Sandbox output
    policy_scores: Annotated[list[dict], add]     # scores for all 15 moves
    conversation_logs: Annotated[list[dict], add]  # i1,i2,i3 per move (saved)

    # Final output
    recommended_moves: list[dict]    # top 3
    other_moves: list[dict]          # remaining 12

    # SSE tracking
    status_updates: Annotated[list[dict], add]    # real-time status events
```

---

## 5. Data Flow Summary

| Stage | Input | Output | Agents | Parallelism |
|-------|-------|--------|--------|-------------|
| Layer 0 | Company ticker | Synthetic financial data + news data (markdown) | 1 (LLM synthesizer, 2 parallel calls) | Parallel |
| Layer 1 | Raw data | F1 (financial inference) + F2 (trend inference) | 2 | Parallel |
| Layer 2 | F1 + F2 | m1.md – m15.md (15 move suggestions) | 5 | Parallel |
| Sandbox (L3+L4) | One mx.md at a time | Score (out of 120) + conversation logs (i1, i2, i3) | 1 critic + 3 DMs | Policies: sequential. Within round: parallel |
| Output | All 15 scores | Top 3 + Other 12 | 0 | N/A |

---

## 6. Technology Stack

| Component | Technology |
|-----------|-----------|
| Agent Orchestration | LangGraph (StateGraph, Send, subgraphs) |
| Backend Framework | FastAPI (Python) |
| LLM Provider | Anthropic Claude Haiku (`claude-haiku-4-5`) via Anthropic Python SDK |
| Agent Sandboxing | microVM sandboxes (provider-agnostic SDK) |
| Real-time Communication | SSE (Server-Sent Events) |
| Frontend | NextJS (App Router) |
| UI Components | shadcn/ui + Tailwind CSS + Framer Motion |
| State Management (FE) | React hooks + SSE stream |

---

## 7. Sandbox Integration Points

The **sandbox layer** (Layer 3+4 negotiation) runs each policy negotiation inside an isolated microVM sandbox:

1. **Sandbox Creation:** When the sandbox orchestrator begins processing a policy, it creates (or reuses) a sandbox via the provider SDK (e.g. `SandboxInstance.create_if_not_exists()`).
2. **Conversation Log Storage:** Intermediate conversation documents (i1, i2, i3) are stored in the sandbox filesystem during the 10-round negotiation.
3. **Process Isolation:** Each negotiation cycle runs in an isolated microVM, preventing cross-contamination between policy evaluations.
4. **Persistence:** After 10 rounds, conversation logs and scores are extracted from the sandbox and persisted to the parent state for frontend display.
5. **Scale-to-Zero:** Sandboxes automatically scale down between policy negotiations, minimizing cost.

```python
from sandbox_provider.core import SandboxInstance  # your sandbox provider SDK

# Create sandbox for a negotiation session
sandbox = await SandboxInstance.create_if_not_exists({
    "name": f"negotiation-{ticker}-{move_id}",
    "image": "sandbox/base-image:latest",
    "memory": 2048,
    "labels": {"ticker": ticker, "move": move_id, "layer": "sandbox"}
})
```

---

## 8. SSE Event Stream Design

The backend emits structured SSE events as the pipeline progresses. The frontend consumes these to update the layer visualization in real time.

**Event types:**

| Event | Payload | When |
|-------|---------|------|
| `layer_start` | `{layer: 0, status: "running"}` | Layer begins execution |
| `layer_complete` | `{layer: 0, status: "done", artifacts: [...]}` | Layer finishes |
| `agent_start` | `{layer: 2, agent_id: "analyst_3", persona: "..."}` | Individual agent starts |
| `agent_complete` | `{layer: 2, agent_id: "analyst_3", output: "m7.md"}` | Agent finishes |
| `sandbox_round` | `{move: "m1", round: 3, status: "critic_responding"}` | Sandbox round progress |
| `sandbox_scored` | `{move: "m1", score: 98, breakdown: {...}}` | Policy scored |
| `pipeline_complete` | `{recommended: [...], other: [...]}` | Full pipeline done |

---

## 9. Security & Isolation

- All LLM-generated content (move suggestions, critic responses, DM rebuttals) is treated as untrusted text.
- Sandboxing provides **kernel-level isolation** via microVMs (not containers), following a zero-trust model.
- API keys and secrets are stored in environment variables, never committed to code.
- The frontend never directly calls LLM APIs; all LLM interactions go through the FastAPI backend.
