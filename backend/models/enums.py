"""
Enumerations used across the application.

See: docs/architecture/LLD_sandbox.md § 6 (scoring metrics)
"""

from enum import Enum


class ScoringMetric(str, Enum):
    IMPACT = "impact"
    FEASIBILITY = "feasibility"
    RISK_ADJUSTED_RETURN = "risk_adjusted_return"
    STRATEGIC_ALIGNMENT = "strategic_alignment"


class RiskLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class LayerStatus(str, Enum):
    IDLE = "idle"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


class PipelineEvent(str, Enum):
    LAYER_START = "layer_start"
    LAYER_COMPLETE = "layer_complete"
    AGENT_START = "agent_start"
    AGENT_COMPLETE = "agent_complete"
    SANDBOX_ROUND = "sandbox_round"
    SANDBOX_SCORED = "sandbox_scored"
    PIPELINE_COMPLETE = "pipeline_complete"
    PIPELINE_ERROR = "pipeline_error"
