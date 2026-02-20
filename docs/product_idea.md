# AI Consulting Agency — Multi-Layer Agent System

## Overview

The system is an AI-powered consulting agency that generates, debates, and ranks strategic business moves for a publicly listed company. The user provides a **company ticker** as input. The system is structured as a sequential pipeline of agent layers — similar in concept to a neural network — where each layer refines the output of the previous one. The final output is a ranked set of strategic recommendations backed by deep reasoning and adversarial debate.

**Pipeline:** Layer 0 → Layer 1 → Layer 2 → Sandbox (Layer 3 + Layer 4) → Final Output

---

## Layer Zero — Data Gathering

Layer 0 is the foundation. It contains no reasoning agents — only data scraper scripts and API calls that collect raw data about the target company. The data falls into two categories:

**Data Source 1 — Financial Data:**
- Numerical data such as quarterly revenue tables, earnings releases, balance sheet snapshots, and other publicly available financial metrics.
- Format: CSV tables, JSON, or Markdown (to be finalized).

**Data Source 2 — News & Sentiment Data:**
- News articles and headlines specifically about the target company.
- Trending discussions on platforms like Reddit.
- Prediction market data from platforms like Polymarket (odds on company-related events).
- News and trends about the company's major competitors.

The specific free APIs to be used for data collection will be decided later. Layer 0's only job is to fetch and store this raw data so downstream layers can consume it.

---

## Layer One — Inference from Raw Data

Layer 1 takes the raw data collected by Layer 0 and derives meaning from it. It does not make strategic decisions — it only elaborates on what the data implies.

This layer has **2 agents**, each handling one data source:

**Agent 1 — Financial Inference:**
- Consumes the financial data from Layer 0.
- Surfaces insights like: "Q2 revenue is declining by X%," "cost structure has improved quarter-over-quarter," "acquisition spending is trending upward," etc.
- Output: **F1** — a Financial Inference Markdown file.

**Agent 2 — Trend / Sentiment Inference:**
- Consumes the news, Reddit, Polymarket, and competitor data from Layer 0.
- Surfaces insights like: "market sentiment is shifting bearish on the sector," "a major competitor just announced expansion into segment X," "Polymarket is pricing in a 70% chance of a regulatory event," etc.
- Output: **F2** — a Trend Inference Markdown file.

These two agents can run **in parallel** since their tasks are independent.

F1 and F2 are the sole inputs to Layer 2.

---

## Layer Two — Analyst Agents

Layer 2 performs the work of business analysts. It takes F1 and F2 as input and generates concrete strategic move suggestions for the company.

This layer has **5 agents** (as a working example — the count can be adjusted). Each agent has a **distinct persona** defined in its system prompt. The personas in this layer are **unbiased** — they are not skewed toward any particular risk appetite. Their job is to analyze the data objectively from their unique perspective.

**Each agent produces 3 move suggestions:**
1. A **low-risk** move
2. A **medium-risk** move
3. A **high-risk** move

**Every move must include:**
- In-depth reasoning explaining why this move should be taken.
- Direct citations from F1 and F2 that support the reasoning.
- The reasoning must be substantive and demonstrate genuine analytical depth — not generic advice that looks like a simple ChatGPT response.

**Output:** 5 agents x 3 moves = **15 move suggestion documents**, named **m1.md, m2.md, m3.md, ... m15.md**. Each is a standalone Markdown file with the move and its full justification.

The 5 agents can run **in parallel** since their tasks are independent — they all read the same F1 and F2 but produce moves based on their own persona.

---

## Layer Three — Critic Agent

Layer 3 contains a **single Critic agent**. Its job is purely adversarial: for any move suggestion (mx.md), it identifies weaknesses in the reasoning, challenges assumptions, and raises counterpoints.

**Persona:** The Critic is sharp, intellectually honest, and thorough — think of a seasoned CFO who has seen companies fail. It is not a contrarian for the sake of it; it genuinely probes the quality of each move by demanding justification and exposing gaps.

Layer 3 does not operate alone. It works in tandem with Layer 4 inside a sandbox.

---

## Layer Four — Decision Maker Agents

Layer 4 contains **3 Decision Maker agents** that represent a board of directors. Their role is to **defend** move suggestions against the Critic's counterpoints. All three are moderately-to-strongly biased toward high-impact, high-growth decisions, but each evaluates moves through a **different lens**:

**Agent D1 — Growth Strategist:**
- Evaluates moves through the lens of market expansion, competitive advantage, and long-term positioning.
- Fights hard for bold moves but can be swayed by strong market-timing arguments.

**Agent D2 — Operational Pragmatist:**
- Evaluates moves through the lens of execution feasibility, resource allocation, and operational risk.
- Favors action but respects constraints. The Critic can get to this agent by pointing out execution gaps.

**Agent D3 — Stakeholder Value Advocate:**
- Evaluates moves through the lens of shareholder return, brand impact, and public perception.
- Biased toward high-visibility wins but sensitive to reputational risk.

The personas are strong enough to stand their ground against the Critic, but they are instructed to **engage substantively** with counterpoints rather than dismiss them. This ensures healthy debate rather than two sides talking past each other.

Layer 4 does not operate alone. It works in tandem with Layer 3 inside a sandbox.

---

## Sandbox — Layer Three + Layer Four Working Together

Layer 3 (Critic) and Layer 4 (Decision Makers) are sandboxed together. They process **one move suggestion at a time**. For each of the 15 move documents (m1.md through m15.md), the sandbox runs a full negotiation cycle.

### Conversation Documents

Three conversation logs are maintained in buffer (as JSON) throughout the negotiation:
- **i1** — shared conversation between Critic and D1
- **i2** — shared conversation between Critic and D2
- **i3** — shared conversation between Critic and D3

Each log is a single shared document. When the Critic says something, it is appended (tagged as Critic). When the Decision Maker responds, it is appended (tagged as D1/D2/D3). On every LLM call, the full conversation log is passed to the model along with the agent's system prompt (persona).

### How Negotiations Work

**Round 1:**
1. The Critic reads the move document (mx.md) and generates a single set of counterpoints.
2. This response is appended to **all three** conversation logs (i1, i2, i3) — since no divergence has occurred yet.
3. Each Decision Maker then reads their respective conversation log and responds based on their persona:
   - D1 reads i1 → responds → response appended to i1
   - D2 reads i2 → responds → response appended to i2
   - D3 reads i3 → responds → response appended to i3
4. At this point, i1, i2, and i3 have **diverged** — each now contains a different Decision Maker's rebuttal.

**Rounds 2–10:**
1. The Critic reads each conversation log **separately** and generates an **individual response** for each Decision Maker:
   - Critic reads i1 → generates response for D1 → appended to i1
   - Critic reads i2 → generates response for D2 → appended to i2
   - Critic reads i3 → generates response for D3 → appended to i3
2. Each Decision Maker then reads their updated conversation log and responds:
   - D1 reads i1 → responds → appended to i1
   - D2 reads i2 → responds → appended to i2
   - D3 reads i3 → responds → appended to i3
3. This constitutes one round. A **round** = one Critic turn + one Decision Maker turn across all three threads.

**Parallelism within rounds:** Since i1, i2, and i3 are independent, the 3 Critic calls within a round can run in parallel. Similarly, the 3 Decision Maker calls can run in parallel. Each round is therefore **2 parallel batches of 3 LLM calls**, not 6 sequential calls.

### Scoring System

After the 10th round of negotiation, each of the 3 Decision Maker agents scores the move on **4 metrics**, each rated out of 10:

| Metric | What it measures |
|---|---|
| **Impact** | How significant is the effect on the company's growth, revenue, or market position? |
| **Feasibility** | How realistic is it to execute given current resources, timeline, and constraints? |
| **Risk-Adjusted Return** | How favorable is the potential upside relative to the downside exposure? |
| **Strategic Alignment** | How well does the move fit the company's long-term direction and competitive positioning? |

- Each agent scores out of **40** (4 metrics x 10 points).
- 3 agents means each move is scored out of **120** (40 x 3).
- The score is recorded for that move, and the process repeats for all 15 moves.
- Total negotiation: approximately **150 rounds** (15 moves x 10 rounds each).

### Saving Conversation Logs

After the 10 rounds for a given move are complete, the conversation logs (i1, i2, i3) are **saved persistently** (not just kept in buffer). These are needed by the frontend to display the negotiation history as proof of reasoning and integrity behind each score.

---

## Final Output

Once all 15 moves have been negotiated and scored, the moves are ranked by total score (out of 120).

- **Top 3** highest-scored moves → presented to the user as **Recommended Next Moves** (full Markdown files with reasoning).
- **Remaining 12** moves → listed as **Other Moves** for consideration (ranked by score, available for review).

---

## Execution Flow Summary

All layers invoke **sequentially**, with specific parallelism within layers:

```
Layer 0 (Data Gathering)          — sequential, runs first
    ↓
Layer 1 (Inference)               — 2 agents run in PARALLEL (F1 + F2)
    ↓
Layer 2 (Analyst)                 — 5 agents run in PARALLEL (m1–m15)
    ↓
Sandbox: Layer 3 + 4 (Negotiate)  — 15 moves processed SEQUENTIALLY, one at a time
                                    Within each move: 10 rounds
                                    Within each round: 2 batches of 3 PARALLEL LLM calls
    ↓
Final Output                      — Rank and return top 3 + remaining 12
```

---

## Frontend

- **Input:** User enters a publicly listed company ticker and hits "Analyze."
- **While processing:** The UI displays a visualization of all 4 layers. Clicking on any layer **zooms in** with an ultra-smooth animated transition to show:
  - The progress of each agent within that layer.
  - Intermediate documents produced by that layer (F1, F2, m1–m15, conversation logs, scores).
  - Documents can be viewed inline.
- Clicking the close button **zooms back out** to the full pipeline view with an equally smooth transition.
- **Design:** Minimal text, dark theme, sci-fi / techy aesthetic. Transitions are the hero — they must be buttery smooth.
- **Real-time updates:** Server-Sent Events (SSE) push live status from backend to frontend.

---

## Tech Stack

1. **Agent Orchestration:** LangGraph
2. **Backend:** LangGraph + Python, wrapped in FastAPI
3. **Frontend:** NextJS
4. **Real-time Communication:** SSE (Server-Sent Events)

---

## Reference: Old Repository Context

We have an existing codebase in a separate repository that implements a 1-to-N negotiation system: one buyer agent negotiates with N seller agents over 10 rounds, after which the buyer selects the best deal. The current system is structurally similar but reverses the flow:

- In the old system: the single agent (buyer) made the decision. The multi-agent side (sellers) proposed.
- In the new system: the single agent (Critic) challenges. The multi-agent side (Decision Makers) defends and scores.

Key architectural difference: the old buyer agent maintained **one shared conversation** (since it needed awareness of all seller proposals). The new Critic agent maintains **three separate conversations** (i1, i2, i3) since each debate is independent.

The code from the old repository will be added to a **separate branch**. When that happens, the team will review it and extract/replicate relevant logic into the main feature branch rather than building from scratch.
