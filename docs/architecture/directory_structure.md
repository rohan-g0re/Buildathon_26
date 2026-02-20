# Project Directory Structure

Ultra modular layout. Every layer is its own package. Every concern is its own file.

```
Buildathon/
│
├── docs/
│   ├── product_idea.md                        # Product spec (source of truth)
│   └── architecture/
│       ├── HLD.md                             # High-level design
│       ├── LLD_layer_0.md                     # Layer 0 detailed design
│       ├── LLD_layer_1.md                     # Layer 1 detailed design
│       ├── LLD_layer_2.md                     # Layer 2 detailed design
│       ├── LLD_sandbox.md                     # Sandbox (L3+L4) detailed design
│       ├── LLD_pipeline.md                    # Pipeline orchestration + API design
│       ├── LLD_frontend.md                    # Frontend design
│       └── directory_structure.md             # This file
│
├── backend/
│   ├── pyproject.toml                         # Python project config (deps, metadata)
│   ├── requirements.txt                       # Pinned dependencies
│   ├── .env.example                           # Template for environment variables
│   ├── main.py                                # FastAPI entrypoint
│   │
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py                        # Pydantic Settings: env vars, API keys, model config
│   │   └── personas.py                        # All agent persona definitions (system prompts)
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── state.py                           # LangGraph state schemas (PipelineState, SandboxState, etc.)
│   │   ├── schemas.py                         # Pydantic models for FastAPI request/response
│   │   └── enums.py                           # Enums: ScoringMetric, RiskLevel, LayerStatus
│   │
│   ├── graph/
│   │   ├── __init__.py
│   │   ├── pipeline.py                        # Main LangGraph StateGraph — parent pipeline definition
│   │   │
│   │   ├── layer_0/
│   │   │   ├── __init__.py
│   │   │   ├── node.py                        # Layer 0 node function for LangGraph
│   │   │   └── scrapers/
│   │   │       ├── __init__.py
│   │   │       ├── financial.py               # Financial data scraper (quarterly reports, etc.)
│   │   │       └── news.py                    # News + sentiment scraper (news APIs, Reddit, Polymarket)
│   │   │
│   │   ├── layer_1/
│   │   │   ├── __init__.py
│   │   │   ├── node.py                        # Layer 1 node: dispatches 2 parallel agents via Send
│   │   │   ├── reduce.py                      # Reducer node: collects F1 + F2 into parent state
│   │   │   ├── financial_inference.py         # Financial inference agent (produces F1)
│   │   │   └── trend_inference.py             # Trend inference agent (produces F2)
│   │   │
│   │   ├── layer_2/
│   │   │   ├── __init__.py
│   │   │   ├── node.py                        # Layer 2 node: dispatches 5 parallel agents via Send
│   │   │   ├── reduce.py                      # Reducer node: collects m1–m15 into parent state
│   │   │   └── analyst_agent.py               # Analyst agent logic (reused with different personas)
│   │   │
│   │   └── sandbox/
│   │       ├── __init__.py
│   │       ├── orchestrator.py                # Iterates over 15 moves, invokes subgraph per move
│   │       ├── subgraph.py                    # LangGraph subgraph: negotiation loop (10 rounds)
│   │       ├── critic.py                      # Critic agent logic (round 1 shared + rounds 2-10 individual)
│   │       ├── decision_maker.py              # Decision maker agent logic (D1, D2, D3)
│   │       ├── scoring.py                     # Scoring logic (4 metrics, aggregation)
│   │       └── conversation.py                # Conversation log management (i1, i2, i3 append/read)
│   │
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py                            # Base agent class: system prompt + LLM call wrapper
│   │   └── llm.py                             # LLM client factory (OpenAI, Anthropic, etc.)
│   │
│   ├── sandbox/
│   │   ├── __init__.py
│   │   └── sandbox_manager.py                 # Sandbox provider wrapper: create, get, delete sandboxes
│   │
│   ├── api/
│   │   ├── __init__.py
│   │   ├── routes.py                          # FastAPI route definitions (/analyze, /status, /results)
│   │   └── sse.py                             # SSE stream manager: event queue, broadcast
│   │
│   └── utils/
│       ├── __init__.py
│       ├── documents.py                       # Markdown doc generation, F1/F2/mx template formatting
│       └── logger.py                          # Structured logging setup
│
├── frontend/
│   ├── package.json
│   ├── next.config.js
│   ├── tailwind.config.ts
│   ├── tsconfig.json
│   ├── postcss.config.js
│   ├── .env.local.example                     # Template for frontend env vars
│   │
│   ├── public/
│   │   └── ...                                # Static assets (fonts, icons)
│   │
│   └── src/
│       ├── app/
│       │   ├── layout.tsx                     # Root layout (dark theme, fonts, global providers)
│       │   ├── page.tsx                       # Landing page: ticker input → "Analyze"
│       │   └── analysis/
│       │       └── [ticker]/
│       │           └── page.tsx               # Analysis dashboard (pipeline vis + results)
│       │
│       ├── components/
│       │   ├── ui/                            # shadcn/ui primitives (Button, Card, Dialog, etc.)
│       │   │
│       │   ├── pipeline/
│       │   │   ├── PipelineView.tsx           # Top-level: 4 layer cards in a row
│       │   │   ├── LayerCard.tsx              # Individual layer card (status, progress ring)
│       │   │   ├── LayerDetail.tsx            # Zoomed-in view: agents + documents inside a layer
│       │   │   ├── AgentNode.tsx              # Single agent status indicator (running/done/idle)
│       │   │   ├── DocumentViewer.tsx         # Renders a markdown document inline
│       │   │   └── ConnectionLine.tsx         # Animated connection line between layers
│       │   │
│       │   ├── input/
│       │   │   └── TickerInput.tsx            # Company ticker input with autocomplete
│       │   │
│       │   └── output/
│       │       ├── RecommendedMoves.tsx       # Top 3 moves: cards with score + reasoning
│       │       ├── OtherMoves.tsx             # Remaining 12 moves: collapsed list
│       │       ├── MoveCard.tsx               # Individual move card (score breakdown, expand)
│       │       └── ScoreBreakdown.tsx         # 4-metric radar/bar chart per move
│       │
│       ├── hooks/
│       │   ├── useSSE.ts                      # SSE connection hook (connect, parse events, reconnect)
│       │   ├── useAnalysis.ts                 # Analysis state machine (idle → running → done)
│       │   └── usePipelineZoom.ts             # Zoom state management (which layer is zoomed)
│       │
│       ├── lib/
│       │   ├── api.ts                         # API client (POST /analyze, GET /results/:ticker)
│       │   ├── types.ts                       # TypeScript interfaces mirroring backend schemas
│       │   └── constants.ts                   # Layer names, colors, animation durations
│       │
│       └── styles/
│           └── globals.css                    # Tailwind base + custom animations + dark theme
│
└── .gitignore
```

---

## Design Principles

1. **One file, one responsibility.** No file does two things. `critic.py` is the critic. `scoring.py` is scoring. Period.

2. **Layers are packages.** Each layer (`layer_0/`, `layer_1/`, `layer_2/`, `sandbox/`) is a self-contained Python package with its own `__init__.py`. You can develop and test each layer in isolation.

3. **Agents are reusable.** `analyst_agent.py` is a single file reused 5 times with different personas. `decision_maker.py` is reused 3 times with different personas. Persona definitions live in `config/personas.py`, not inside agent files.

4. **State schemas are centralized.** All LangGraph state types live in `models/state.py`. All Pydantic API models live in `models/schemas.py`. No inline TypedDicts scattered across files.

5. **Graph definition is separate from agent logic.** `graph/pipeline.py` defines the topology (nodes + edges). Individual agent logic lives in layer-specific files. The pipeline file imports and wires them.

6. **Sandboxing is abstracted.** All sandbox provider SDK calls go through `sandbox/sandbox_manager.py`. If you swap sandboxing providers, you change one file.

7. **Frontend components are atomic.** `PipelineView` composes `LayerCard`s. `LayerDetail` composes `AgentNode`s and `DocumentViewer`s. Each component is a single `.tsx` file.
