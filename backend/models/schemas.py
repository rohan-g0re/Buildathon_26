"""
Pydantic models for FastAPI request/response schemas.

See: docs/architecture/LLD_pipeline.md § 7
"""

from pydantic import BaseModel
from typing import Any, Optional


class AnalyzeRequest(BaseModel):
    """POST /api/analyze request body."""
    ticker: str  # e.g., "AAPL", "TSLA"


class AnalyzeResponse(BaseModel):
    """POST /api/analyze response body."""
    analysis_id: str
    ticker: str
    status: str          # "running"
    sse_url: str         # "/api/stream/{analysis_id}"


class ScoreBreakdown(BaseModel):
    """Score breakdown for a single decision maker agent."""
    impact: int
    feasibility: int
    risk_adjusted_return: int
    strategic_alignment: int


class MoveResult(BaseModel):
    """A scored move in the final output."""
    move_id: str
    total_score: int
    scores_by_agent: dict[str, Any]
    move_document: dict
    skipped: Optional[bool] = None
    reason: Optional[str] = None


class AnalysisResult(BaseModel):
    """Analysis results — populated incrementally as layers complete."""
    recommended_moves: list[dict] = []
    other_moves: list[dict] = []
    f1: str = ""
    f2: str = ""
    move_suggestions: list[dict] = []
    conversation_logs: list[dict] = []
    financial_data_raw: str = ""
    news_data_raw: str = ""


class AnalysisStatus(BaseModel):
    """GET /api/results/:id response body."""
    analysis_id: str
    ticker: str
    status: str                           # "running" | "complete" | "error"
    result: Optional[AnalysisResult] = None
