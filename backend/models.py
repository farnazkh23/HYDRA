from datetime import datetime
from enum import Enum
from typing import Any
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SignalType(str, Enum):
    NEWS = "news"
    SANCTION = "sanction"
    DOMAIN_CHANGE = "domain_change"
    REGISTRY = "registry"
    FUNDING = "funding"
    TRANSACTION = "transaction"


class RiskLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertAction(str, Enum):
    APPROVE = "approve"
    ESCALATE = "escalate"
    DISMISS = "dismiss"


class KYCRiskRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RouterPath(str, Enum):
    DROPPED = "dropped"          # Loop A filtered it out — stable, no drift
    FAST_CLASSIFIER = "fast"     # Loop B: T >= 7 days, lightweight model
    HEAVY_REASONER = "heavy"     # Loop B: T < 7 days or high uncertainty → DeepSeek-R1


# ---------------------------------------------------------------------------
# KYC Profile — simulated internal bank data (Layer 2)
# ---------------------------------------------------------------------------

class KYCProfile(BaseModel):
    client_id: str
    name: str
    industry: str
    jurisdiction: str                          # ISO 2-letter country code
    legal_form: str                            # e.g. "GmbH", "Ltd", "SA"
    incorporation_date: str                    # ISO date string
    expected_monthly_volume_usd: int
    primary_currencies: list[str]
    business_model: str
    beneficial_owners: list[str]
    risk_rating: KYCRiskRating
    onboarding_date: str
    website: str
    notes: str = ""


# ---------------------------------------------------------------------------
# KYC Drift — tracks what changed vs the original KYC baseline
# ---------------------------------------------------------------------------

class KYCDriftField(BaseModel):
    field: str                                 # e.g. "beneficial_owners", "jurisdiction"
    baseline_value: str                        # what was on file at onboarding
    current_value: str                         # what was detected now
    drift_severity: RiskLevel                  # how significant is this change
    source: str                                # where was the change detected


class KYCDriftRecord(BaseModel):
    client_id: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    drifted_fields: list[KYCDriftField]
    overall_drift_severity: RiskLevel
    rekyc_required: bool
    summary: str                               # human-readable: "Beneficial owner changed from X to Y"


# ---------------------------------------------------------------------------
# RawSignal — produced by collectors, consumed by HYDRA stream_engine
# ---------------------------------------------------------------------------

class RawSignal(BaseModel):
    entity_name: str
    client_id: str
    signal_type: SignalType
    source: str                                # e.g. "NewsAPI", "OpenSanctions"
    content: str                               # raw text or summary
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# AI Reasoning Trace — step-by-step pipeline trace shown on the frontend
# ---------------------------------------------------------------------------

class LoopATrace(BaseModel):
    """Trace from HYDRA Loop A: High-Frequency Latent Regime Detection."""
    vae_reconstruction_error: float            # raw VAE loss value
    drift_threshold: float                     # dynamic variance threshold at this moment
    drift_detected: bool                       # True → DRIFT_EVENT emitted; False → signal dropped
    top_keywords_matched: list[str]            # high-risk keywords/entities that fired
    embedding_shift_score: float               # cosine distance from baseline latent centroid
    decision: str                              # "DRIFT_EVENT emitted" or "Signal dropped — stable"
    tokens_used: int = 0
    cost_usd: float = 0.0


class GraphRAGStep(BaseModel):
    """One step of the temporal knowledge graph reasoning in Loop B."""
    entity: str
    relationship_change: str                   # e.g. "new beneficial owner added"
    triple_status: str                         # "added" | "deleted" | "unchanged"
    cypher_query: str                          # the actual Neo4j query that ran
    timestamp_slice: str                       # the time window this triple covers


class LoopBTrace(BaseModel):
    """Trace from HYDRA Loop B: Predictive GraphRAG & Deep Survival Inference."""
    # GraphRAG
    graph_steps: list[GraphRAGStep]
    graph_summary: str                         # LLM-generated summary of graph changes

    # TimeGPT forecasting
    timegpt_forecast_horizon_days: int
    timegpt_anomaly_score: float
    timegpt_uncertainty_interval: tuple[float, float]
    timegpt_summary: str                       # e.g. "Transaction volume projected to spike 3× in 5 days"

    # Survival model
    survival_model_used: str                   # "SumoNet" | "DeepSurv" | "ConSurv"
    time_to_decay_days: float                  # T — the key output
    survival_confidence: float
    survival_summary: str                      # e.g. "KYC compliance expected to decay in 4.2 days"

    # Router decision
    router_path: RouterPath
    router_reason: str                         # why this path was chosen

    # LLM (only populated for fast/heavy paths)
    model_used: str | None = None              # e.g. "deepseek-r1", "claude-haiku-4-5"
    tokens_used: int = 0
    cost_usd: float = 0.0


class AIReasoningTrace(BaseModel):
    """
    Complete, step-by-step record of how HYDRA processed one signal.
    This is the primary model for the frontend's explainability panel.
    """
    trace_id: str
    alert_id: str
    client_id: str

    loop_a: LoopATrace
    loop_b: LoopBTrace | None = None           # None if Loop A dropped the signal

    # Final structured output from Outlines / Instructor
    chain_of_thought: str                      # full CoT block forced by structured generation
    audit_citations: list[dict[str, str]]      # [{"url": ..., "excerpt": ..., "source": ...}]
    guardrail_checks: list[str]                # e.g. ["no hallucinated entities", "all citations verified"]
    bias_flags: list[str]                      # any detected bias warnings
    hallucination_check_passed: bool

    # Aggregate cost for this one signal end-to-end
    total_tokens_used: int
    total_cost_usd: float

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Governance Record — compliance workflow trail for each alert
# ---------------------------------------------------------------------------

class GovernanceStep(BaseModel):
    """One step in the human-in-the-loop compliance workflow."""
    step: str                                  # e.g. "Initial AI Flag", "Compliance Review", "Escalation"
    actor: str                                 # role or system that performed this step
    action: str                                # what was done
    outcome: str                               # result of this step
    note: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GovernanceRecord(BaseModel):
    """
    Full compliance governance trail for one alert.
    Satisfies the challenge's Decision Governance requirement.
    """
    record_id: str
    alert_id: str
    client_id: str
    status: str                                # "pending" | "under_review" | "escalated" | "closed"
    steps: list[GovernanceStep]
    requires_manual_approval: bool
    approval_deadline: datetime | None = None
    final_decision: str | None = None          # "approved" | "escalated" | "dismissed"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# RiskAlert — the central model: produced by HYDRA, consumed by API + frontend
# ---------------------------------------------------------------------------

class RiskAlert(BaseModel):
    alert_id: str
    client_id: str

    # Core risk assessment
    risk_score: float = Field(ge=0.0, le=10.0)
    risk_level: RiskLevel
    signal_type: str                           # human-readable flag label
    explanation: str                           # plain English summary for compliance officer
    recommended_action: str
    confidence: float = Field(ge=0.0, le=1.0)

    # Originating data
    raw_signal: RawSignal | None = None

    # KYC drift (populated if structural changes were detected)
    kyc_drift: KYCDriftRecord | None = None

    # Full AI reasoning trace — drives the frontend explainability panel
    reasoning_trace: AIReasoningTrace | None = None

    # Governance workflow
    governance: GovernanceRecord | None = None

    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AlertActionRecord — written to audit log when a user acts on an alert
# ---------------------------------------------------------------------------

class AlertActionRecord(BaseModel):
    record_id: str
    alert_id: str
    client_id: str
    action: AlertAction
    actor: str = "compliance_officer"
    note: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# API response wrappers
# ---------------------------------------------------------------------------

class ClientRiskSummary(BaseModel):
    client_id: str
    name: str
    current_risk_score: float
    risk_level: RiskLevel
    open_alerts: int
    kyc_drift_detected: bool
    last_updated: datetime | None


class CostTracker(BaseModel):
    stage: str                                 # "loop_a" | "loop_b_fast" | "loop_b_heavy"
    model_used: str
    tokens_used: int
    estimated_cost_usd: float
    calls: int
    cost_per_1000_analyses_usd: float          # judges explicitly look for this
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CostSummary(BaseModel):
    """Aggregate cost breakdown shown in the frontend cost tracker panel."""
    total_signals_processed: int
    total_dropped_by_loop_a: int               # how many were filtered cheaply
    total_escalated_to_loop_b: int
    total_tokens_used: int
    total_cost_usd: float
    cost_per_1000_analyses_usd: float
    breakdown: list[CostTracker]
    as_of: datetime = Field(default_factory=datetime.utcnow)
