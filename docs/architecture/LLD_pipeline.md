# Low-Level Design — Pipeline Orchestration, API, and SSE

## 1. Purpose

This document covers the **glue** — how the LangGraph pipeline is assembled, how FastAPI exposes it, and how SSE streams real-time updates to the frontend.

---

## 2. Complete LangGraph Pipeline Definition

```python
# graph/pipeline.py

from langgraph.graph import StateGraph, START, END
from models.state import PipelineState

# Layer 0
from graph.layer_0.node import layer_0_synthesize

# Layer 1
from graph.layer_1.node import dispatch_layer_1
from graph.layer_1.financial_inference import financial_inference_agent
from graph.layer_1.trend_inference import trend_inference_agent
from graph.layer_1.reduce import layer_1_reduce

# Layer 2
from graph.layer_2.node import dispatch_layer_2
from graph.layer_2.analyst_agent import analyst_agent
from graph.layer_2.reduce import layer_2_reduce

# Sandbox (Layer 3 + 4)
from graph.sandbox.orchestrator import sandbox_orchestrator

# Output
from graph.output import rank_and_output


def build_pipeline() -> StateGraph:
    """
    Assembles the full agent pipeline.

    Topology:
    START → layer_0 → [layer_1 fan-out (2 parallel)] → layer_1_reduce
          → [layer_2 fan-out (5 parallel)] → layer_2_reduce
          → sandbox_orchestrator → rank_and_output → END
    """
    builder = StateGraph(PipelineState)

    # ── NODES ──────────────────────────────────────────────────
    builder.add_node("layer_0_gather", layer_0_synthesize)
    builder.add_node("financial_inference_agent", financial_inference_agent)
    builder.add_node("trend_inference_agent", trend_inference_agent)
    builder.add_node("layer_1_reduce", layer_1_reduce)
    builder.add_node("analyst_agent", analyst_agent)
    builder.add_node("layer_2_reduce", layer_2_reduce)
    builder.add_node("sandbox_orchestrator", sandbox_orchestrator)
    builder.add_node("rank_and_output", rank_and_output)

    # ── EDGES ──────────────────────────────────────────────────

    # Entry → Layer 0
    builder.add_edge(START, "layer_0_gather")

    # Layer 0 → Layer 1 (fan-out to 2 parallel inference agents)
    builder.add_conditional_edges("layer_0_gather", dispatch_layer_1)

    # Both inference agents → Layer 1 reduce
    builder.add_edge("financial_inference_agent", "layer_1_reduce")
    builder.add_edge("trend_inference_agent", "layer_1_reduce")

    # Layer 1 reduce → Layer 2 (fan-out to 5 parallel analyst agents)
    builder.add_conditional_edges("layer_1_reduce", dispatch_layer_2)

    # All analyst agents → Layer 2 reduce
    builder.add_edge("analyst_agent", "layer_2_reduce")

    # Layer 2 reduce → Sandbox orchestrator
    builder.add_edge("layer_2_reduce", "sandbox_orchestrator")

    # Sandbox → Rank and output
    builder.add_edge("sandbox_orchestrator", "rank_and_output")

    # Output → END
    builder.add_edge("rank_and_output", END)

    return builder.compile()


pipeline = build_pipeline()
```

---

## 3. Rank and Output Node

```python
# graph/output.py

from models.state import PipelineState

def rank_and_output(state: PipelineState) -> dict:
    """
    Takes all 15 scored policies, sorts by total_score descending,
    and splits into top 3 (recommended) and remaining 12 (other).
    """
    scores = state["policy_scores"]
    moves = state["move_suggestions"]

    # Create a lookup: move_id → move document
    move_lookup = {m["move_id"]: m for m in moves}

    # Sort scores descending
    ranked = sorted(scores, key=lambda s: s["total_score"], reverse=True)

    # Attach move document to each score
    for score_entry in ranked:
        score_entry["move_document"] = move_lookup.get(score_entry["move_id"], {})

    # Split top 3 vs rest
    recommended = ranked[:3]
    other = ranked[3:]

    return {
        "recommended_moves": recommended,
        "other_moves": other,
        "status_updates": [
            {"event": "pipeline_complete",
             "recommended": [r["move_id"] for r in recommended],
             "other": [o["move_id"] for o in other]}
        ]
    }
```

---

## 4. FastAPI Application

```python
# main.py

import asyncio
import uuid
from fastapi import FastAPI, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from api.routes import router
from config.settings import settings

app = FastAPI(
    title="AI Consulting Agency",
    description="Multi-layer agent pipeline for strategic business analysis",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api")
```

---

## 5. API Routes

```python
# api/routes.py

from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import AnalyzeRequest, AnalyzeResponse, AnalysisStatus
from api.sse import SSEManager
from graph.pipeline import pipeline
import asyncio
import uuid

router = APIRouter()

# In-memory store for active analyses
active_analyses: dict[str, dict] = {}

sse_manager = SSEManager()


@router.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks
):
    """
    Starts the analysis pipeline for a given ticker.
    Returns an analysis_id for tracking progress via SSE.
    """
    analysis_id = str(uuid.uuid4())

    active_analyses[analysis_id] = {
        "ticker": request.ticker,
        "status": "running",
        "result": None,
    }

    # Run pipeline in background
    background_tasks.add_task(
        _run_pipeline, analysis_id, request.ticker
    )

    return AnalyzeResponse(
        analysis_id=analysis_id,
        ticker=request.ticker,
        status="running",
        sse_url=f"/api/stream/{analysis_id}",
    )


@router.get("/stream/{analysis_id}")
async def stream_progress(analysis_id: str):
    """
    SSE endpoint. Streams real-time status updates for an analysis.
    """
    if analysis_id not in active_analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return StreamingResponse(
        sse_manager.subscribe(analysis_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        }
    )


@router.get("/results/{analysis_id}", response_model=AnalysisStatus)
async def get_results(analysis_id: str):
    """
    Returns the current status and results (if complete) for an analysis.
    """
    if analysis_id not in active_analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    analysis = active_analyses[analysis_id]

    return AnalysisStatus(
        analysis_id=analysis_id,
        ticker=analysis["ticker"],
        status=analysis["status"],
        result=analysis.get("result"),
    )


async def _run_pipeline(analysis_id: str, ticker: str):
    """
    Runs the LangGraph pipeline and streams status updates via SSE.
    """
    try:
        # Stream pipeline execution
        async for event in pipeline.astream(
            {"company_ticker": ticker},
            stream_mode="updates",
        ):
            # Extract status_updates from each node's output
            for node_name, node_output in event.items():
                updates = node_output.get("status_updates", [])
                for update in updates:
                    await sse_manager.publish(analysis_id, update)

        # Get final state
        # (astream consumed the full run; we get the final result)
        final_state = await pipeline.ainvoke({"company_ticker": ticker})

        active_analyses[analysis_id]["status"] = "complete"
        active_analyses[analysis_id]["result"] = {
            "recommended_moves": final_state["recommended_moves"],
            "other_moves": final_state["other_moves"],
            "f1": final_state["f1_financial_inference"],
            "f2": final_state["f2_trend_inference"],
            "conversation_logs": final_state["conversation_logs"],
        }

        await sse_manager.publish(analysis_id, {
            "event": "pipeline_complete",
            "status": "done",
        })

    except Exception as e:
        active_analyses[analysis_id]["status"] = "error"
        await sse_manager.publish(analysis_id, {
            "event": "pipeline_error",
            "error": str(e),
        })
```

---

## 6. SSE Manager

```python
# api/sse.py

import asyncio
import json
from typing import AsyncGenerator

class SSEManager:
    """
    Manages Server-Sent Event streams for multiple concurrent analyses.
    Each analysis_id has its own event queue.
    """

    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = {}

    async def publish(self, analysis_id: str, event: dict):
        """
        Publishes an event to all subscribers of an analysis.
        """
        if analysis_id not in self._queues:
            return

        data = json.dumps(event)
        for queue in self._queues[analysis_id]:
            await queue.put(data)

    async def subscribe(self, analysis_id: str) -> AsyncGenerator[str, None]:
        """
        Returns an async generator that yields SSE-formatted events.
        """
        queue: asyncio.Queue = asyncio.Queue()

        if analysis_id not in self._queues:
            self._queues[analysis_id] = []
        self._queues[analysis_id].append(queue)

        try:
            while True:
                data = await queue.get()

                # SSE format: data: {...}\n\n
                yield f"data: {data}\n\n"

                # Check for terminal events
                parsed = json.loads(data)
                if parsed.get("event") in ("pipeline_complete", "pipeline_error"):
                    break
        finally:
            # Cleanup subscriber
            if analysis_id in self._queues:
                self._queues[analysis_id].remove(queue)
                if not self._queues[analysis_id]:
                    del self._queues[analysis_id]
```

---

## 7. Pydantic Schemas

```python
# models/schemas.py

from pydantic import BaseModel
from typing import Optional

class AnalyzeRequest(BaseModel):
    ticker: str  # e.g., "AAPL", "TSLA"

class AnalyzeResponse(BaseModel):
    analysis_id: str
    ticker: str
    status: str          # "running"
    sse_url: str         # "/api/stream/{analysis_id}"

class ScoreBreakdown(BaseModel):
    impact: int
    feasibility: int
    risk_adjusted_return: int
    strategic_alignment: int

class MoveResult(BaseModel):
    move_id: str
    total_score: int
    scores_by_agent: dict[str, ScoreBreakdown]
    move_document: dict

class AnalysisResult(BaseModel):
    recommended_moves: list[MoveResult]
    other_moves: list[MoveResult]
    f1: str
    f2: str
    conversation_logs: list[dict]

class AnalysisStatus(BaseModel):
    analysis_id: str
    ticker: str
    status: str                           # "running" | "complete" | "error"
    result: Optional[AnalysisResult] = None
```

---

## 8. Configuration

```python
# config/settings.py

from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Server
    host: str = "0.0.0.0"
    port: int = 8000
    cors_origins: list[str] = ["http://localhost:3000"]

    # LLM (Anthropic Claude)
    anthropic_api_key: str = ""          # or set ANTHROPIC_API_KEY in env
    llm_model: str = "claude-haiku-4-5"  # Haiku for prototype speed/cost
    llm_temperature: float = 0.7
    llm_max_retries: int = 3

    # Sandbox (microVM / isolated execution)
    sandbox_workspace: str = ""
    sandbox_api_key: str = ""
    sandbox_region: str = "us-pdx-1"

    # Pipeline
    num_analyst_agents: int = 5
    num_negotiation_rounds: int = 10
    num_decision_makers: int = 3
    top_k_recommendations: int = 3

    class Config:
        env_file = ".env"


settings = Settings()
```

---

## 9. Base Agent / LLM Client (Anthropic SDK)

All LLM calls use the **Anthropic Python SDK** directly (no LangChain wrappers).

```python
# agents/llm.py

from anthropic import AsyncAnthropic
from config.settings import settings

_client: AsyncAnthropic | None = None

def get_anthropic_client() -> AsyncAnthropic:
    """Returns a singleton AsyncAnthropic client."""
    global _client
    if _client is None:
        _client = AsyncAnthropic(api_key=settings.anthropic_api_key)
    return _client
```

```python
# agents/base.py

import asyncio
from agents.llm import get_anthropic_client
from config.settings import settings

async def call_llm(
    system_prompt: str,
    user_prompt: str,
    max_tokens: int = 4096,
    temperature: float | None = None,
    retries: int | None = None,
) -> str:
    """
    Makes a single LLM call via the Anthropic API.
    system_prompt is passed as a top-level `system` parameter.
    Returns the text response. Retries with exponential backoff.
    """
    retries = retries or settings.llm_max_retries
    temperature = temperature if temperature is not None else settings.llm_temperature
    client = get_anthropic_client()

    for attempt in range(retries):
        try:
            message = await client.messages.create(
                model=settings.llm_model,
                max_tokens=max_tokens,
                temperature=temperature,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}],
            )
            return message.content[0].text
        except Exception as e:
            if attempt == retries - 1:
                raise
            wait = 2 ** attempt  # 1s, 2s, 4s
            await asyncio.sleep(wait)
```

---

## 10. Execution Flow (End-to-End)

```
1. User POST /api/analyze {"ticker": "AAPL"}
2. Server returns {analysis_id, sse_url}
3. Frontend connects to SSE: GET /api/stream/{analysis_id}
4. Backend runs LangGraph pipeline in background task
5. Each node emits status_updates → SSE publishes to frontend
6. Layer 0: synthesize data (2 parallel LLM calls) → emit layer_complete
7. Layer 1: 2 parallel inference agents → emit agent_complete x2 → emit layer_complete
8. Layer 2: 5 parallel analyst agents → emit agent_complete x5 → emit layer_complete
9. Sandbox: 15 policies × 10 rounds → emit sandbox_round x150 → emit sandbox_scored x15
10. Rank → emit pipeline_complete with top 3 + other 12
11. Frontend receives pipeline_complete → fetches full results from GET /api/results/{id}
12. SSE stream closes
```
