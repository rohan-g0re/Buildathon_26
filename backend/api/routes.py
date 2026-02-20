"""
FastAPI route definitions.

  POST /api/analyze    — start an analysis pipeline
  GET  /api/stream/:id — SSE stream for real-time progress
  GET  /api/results/:id — fetch completed results

See: docs/architecture/LLD_pipeline.md § 5
"""

import logging
import traceback
import uuid
from fastapi import APIRouter, BackgroundTasks, HTTPException
from fastapi.responses import StreamingResponse
from models.schemas import AnalyzeRequest, AnalyzeResponse, AnalysisStatus
from api.sse import SSEManager
from graph.pipeline import pipeline
from graph.sandbox.orchestrator import set_sse_publish

log = logging.getLogger("pipeline")

router = APIRouter()

# In-memory store for active analyses
active_analyses: dict[str, dict] = {}

sse_manager = SSEManager()


@router.post("/analyze", response_model=AnalyzeResponse)
async def start_analysis(
    request: AnalyzeRequest,
    background_tasks: BackgroundTasks,
):
    """Starts the analysis pipeline for a given ticker."""
    analysis_id = str(uuid.uuid4())

    active_analyses[analysis_id] = {
        "ticker": request.ticker,
        "status": "running",
        "result": None,
    }

    log.info("POST /analyze  ticker=%s  id=%s", request.ticker, analysis_id)
    background_tasks.add_task(_run_pipeline, analysis_id, request.ticker)

    return AnalyzeResponse(
        analysis_id=analysis_id,
        ticker=request.ticker,
        status="running",
        sse_url=f"/api/stream/{analysis_id}",
    )


@router.get("/stream/{analysis_id}")
async def stream_progress(analysis_id: str):
    """SSE endpoint — streams real-time status updates for an analysis."""
    log.info("GET /stream  id=%s", analysis_id)
    if analysis_id not in active_analyses:
        raise HTTPException(status_code=404, detail="Analysis not found")

    return StreamingResponse(
        sse_manager.subscribe(analysis_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/results/{analysis_id}", response_model=AnalysisStatus)
async def get_results(analysis_id: str):
    """Returns the current status and results (if complete) for an analysis."""
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
    Runs the LangGraph pipeline via astream and publishes status_updates
    to SSE subscribers in real time. Accumulates the final state from
    the stream — no double invocation.

    The sandbox orchestrator publishes its own events in real-time via
    the _sse_publish callback, so we skip re-publishing those events
    when the orchestrator node's output arrives.
    """
    short_id = analysis_id[:8]
    log.info("[%s] Pipeline starting for %s", short_id, ticker)

    # ── Wire real-time SSE callback for the sandbox orchestrator ──
    # Events from sandbox_round, sandbox_scored, etc. are published
    # immediately by the orchestrator as each subgraph node finishes.
    async def _sandbox_sse_callback(event: dict):
        event_type = event.get("event", "unknown")
        log.info("[%s] SSE (realtime) -> %s %s", short_id, event_type,
                 {k: v for k, v in event.items() if k != "messages"})
        await sse_manager.publish(analysis_id, event)

    set_sse_publish(_sandbox_sse_callback)

    # Events already published in real-time by the orchestrator.
    # We track them so we don't double-publish when the parent
    # pipeline.astream yields the orchestrator's batched output.
    SANDBOX_REALTIME_EVENTS = {
        "layer_start", "layer_complete",
        "sandbox_round", "sandbox_scored", "sandbox_skipped",
    }

    try:
        final_state: dict = {"company_ticker": ticker}

        # Publish initial layer_start for Layer 0
        await sse_manager.publish(analysis_id, {
            "event": "layer_start", "layer": 0,
        })
        log.info("[%s] SSE -> layer_start layer=0", short_id)

        log.info("[%s] Starting pipeline.astream()...", short_id)

        async for event in pipeline.astream(
            {"company_ticker": ticker},
            stream_mode="updates",
        ):
            for node_name, node_output in event.items():
                # Log what keys this node produced
                keys = list(node_output.keys())
                log.info("[%s] astream node=%s  keys=%s", short_id, node_name, keys)

                # Merge node output into final_state
                for key, value in node_output.items():
                    if key == "status_updates":
                        final_state.setdefault("status_updates", [])
                        final_state["status_updates"].extend(value)
                    elif isinstance(value, list) and isinstance(
                        final_state.get(key), list
                    ):
                        # For Annotated[list, add] fields — extend
                        final_state[key].extend(value)
                    else:
                        final_state[key] = value

                # Publish status_updates to SSE
                # For sandbox_orchestrator, events were already published
                # in real-time by the orchestrator — skip re-publishing.
                is_sandbox_node = (node_name == "sandbox_orchestrator")

                for update in node_output.get("status_updates", []):
                    event_type = update.get("event", "unknown")

                    # Skip events already published in real-time by orchestrator
                    if is_sandbox_node and event_type in SANDBOX_REALTIME_EVENTS:
                        log.info("[%s] SSE (skip dup) %s from %s",
                                 short_id, event_type, node_name)
                        continue

                    layer = update.get("layer", "?")
                    agent_id = update.get("agent_id", "")
                    persona = update.get("persona", "")

                    # Build a meaningful log line depending on event type
                    if event_type == "layer_start":
                        log.info("[%s] SSE -> layer_start layer=%s", short_id, layer)
                    elif event_type == "layer_complete":
                        artifacts = update.get("artifacts", [])
                        total_moves = update.get("total_moves", "")
                        log.info("[%s] SSE -> layer_complete layer=%s status=%s, artifacts=%s%s",
                                 short_id, layer, update.get("status", "done"),
                                 artifacts,
                                 f", total_moves={total_moves}" if total_moves else "")
                    elif event_type == "agent_complete":
                        move_count = update.get("move_count", "")
                        log.info("[%s] SSE -> agent_complete layer=%s agent_id=%s, persona=%s%s",
                                 short_id, layer, agent_id, persona,
                                 f", move_count={move_count}" if move_count else "")
                    elif event_type == "sandbox_round":
                        log.info("[%s] SSE -> sandbox_round move=%s round=%s status=%s",
                                 short_id, update.get("move"), update.get("round"), update.get("status"))
                    elif event_type == "sandbox_scored":
                        log.info("[%s] SSE -> sandbox_scored move=%s score=%s",
                                 short_id, update.get("move"), update.get("score"))
                    elif event_type == "sandbox_skipped":
                        log.info("[%s] SSE -> sandbox_skipped move=%s reason=%s",
                                 short_id, update.get("move"), update.get("reason"))
                    elif event_type == "pipeline_complete":
                        recommended = update.get("recommended", [])
                        log.info("[%s] SSE -> pipeline_complete recommended=%s", short_id, recommended)
                    else:
                        log.info("[%s] SSE -> %s %s", short_id, event_type, update)

                    await sse_manager.publish(analysis_id, update)

                # Log move accumulation
                if "move_suggestions" in node_output:
                    total = len(final_state.get("move_suggestions", []))
                    log.info("[%s]   +%d moves (total: %d)",
                             short_id, len(node_output["move_suggestions"]), total)

                # ── Continuously update partial results so GET /results/:id
                #    returns data as each layer completes (not just at the end).
                active_analyses[analysis_id]["result"] = {
                    "recommended_moves": final_state.get("recommended_moves", []),
                    "other_moves": final_state.get("other_moves", []),
                    "f1": final_state.get("f1_financial_inference", ""),
                    "f2": final_state.get("f2_trend_inference", ""),
                    "move_suggestions": final_state.get("move_suggestions", []),
                    "conversation_logs": final_state.get("conversation_logs", []),
                    "financial_data_raw": final_state.get("financial_data_raw", ""),
                    "news_data_raw": final_state.get("news_data_raw", ""),
                }

        # ── Pipeline finished successfully ──
        moves_count = len(final_state.get("move_suggestions", []))
        recommended_count = len(final_state.get("recommended_moves", []))
        other_count = len(final_state.get("other_moves", []))
        log.info("[%s] Pipeline COMPLETE  moves=%d  recommended=%d  other=%d",
                 short_id, moves_count, recommended_count, other_count)

        active_analyses[analysis_id]["status"] = "complete"

        await sse_manager.publish(analysis_id, {
            "event": "pipeline_complete", "status": "done",
        })

    except Exception as e:
        log.error("[%s] Pipeline FAILED: %s", short_id, e)
        log.error("[%s] Traceback:\n%s", short_id, traceback.format_exc())
        active_analyses[analysis_id]["status"] = "error"
        await sse_manager.publish(analysis_id, {
            "event": "pipeline_error", "error": str(e),
        })
    finally:
        # Clean up the callback so it doesn't hold a reference
        set_sse_publish(None)
