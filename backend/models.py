from datetime import datetime
from enum import Enum
import json
from typing import Any

try:
    from pydantic import BaseModel, ConfigDict, Field
except ModuleNotFoundError:
    def ConfigDict(**kwargs: Any) -> dict[str, Any]:
        return kwargs

    class _FieldInfo:
        def __init__(self, default: Any = None, default_factory: Any = None) -> None:
            self.default = default
            self.default_factory = default_factory

    def Field(default: Any = None, default_factory: Any = None, **_: Any) -> Any:
        return _FieldInfo(default=default, default_factory=default_factory)

    class BaseModel:
        def __init__(self, **data: Any) -> None:
            for cls in reversed(type(self).mro()):
                annotations = getattr(cls, "__annotations__", {})
                for name in annotations:
                    if name in data:
                        setattr(self, name, data.pop(name))
                        continue
                    if hasattr(cls, name):
                        default = getattr(cls, name)
                        if isinstance(default, _FieldInfo):
                            if default.default_factory is not None:
                                setattr(self, name, default.default_factory())
                            elif default.default is not None:
                                setattr(self, name, default.default)
                        elif not callable(default):
                            setattr(self, name, default)
            for name, value in data.items():
                setattr(self, name, value)

        def model_dump(self, mode: str = "python") -> dict[str, Any]:
            return {
                key: _serialize_model_value(value)
                for key, value in self.__dict__.items()
                if not key.startswith("_")
            }

        def json(self) -> str:
            return json.dumps(self.model_dump(mode="json"))


def _serialize_model_value(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return value.model_dump(mode="json")
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, list):
        return [_serialize_model_value(item) for item in value]
    if isinstance(value, tuple):
        return tuple(_serialize_model_value(item) for item in value)
    if isinstance(value, dict):
        return {key: _serialize_model_value(item) for key, item in value.items()}
    return value


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


class DriftSeverity(str, Enum):
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AlertAction(str, Enum):
    APPROVE = "approve"
    ESCALATE = "escalate"
    DISMISS = "dismiss"


class KYCRiskRating(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class RouterPath(str, Enum):
    DROPPED = "dropped"               # Loop A filtered it out — stable, no drift
    FAST_CLASSIFIER = "fast"          # Loop B: T >= 7 days, lightweight model
    HEAVY_REASONER = "heavy"          # Loop B: T < 7 days or high uncertainty → DeepSeek-R1


class RiskTrend(str, Enum):
    INCREASING = "INCREASING"
    STABLE = "STABLE"
    DECREASING = "DECREASING"


class UncertaintyLevel(str, Enum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


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
    drift_severity: RiskLevel
    source: str                                # where was the change detected


class KYCDriftRecord(BaseModel):
    client_id: str
    detected_at: datetime = Field(default_factory=datetime.utcnow)
    drifted_fields: list[KYCDriftField]
    overall_drift_severity: RiskLevel
    rekyc_required: bool
    summary: str


# ---------------------------------------------------------------------------
# RawSignal — produced by collectors, consumed by HYDRA stream_engine
# ---------------------------------------------------------------------------

class RawSignal(BaseModel):
    entity_name: str
    client_id: str
    signal_type: SignalType
    source: str                                # e.g. "event_registry/Reuters", "mock_news"
    content: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict[str, Any] = Field(default_factory=dict)


class Layer1KycBaseline(BaseModel):
    client_id: str
    legal_name: str
    jurisdiction: str
    baseline_business_model: str
    expected_activity: list[str] = Field(default_factory=list)
    expected_keywords: list[str]
    high_risk_keywords: list[str] = Field(default_factory=list)
    expected_jurisdictions: list[str]
    expected_monthly_volume_chf: int
    risk_appetite: str = ""
    expected_transaction_profile: str = ""
    ownership_assumptions: list[str] = Field(default_factory=list)
    monitored_public_entities: list[str] = Field(default_factory=list)
    website: str = ""
    domain: str = ""
    risk_rating: str
    last_kyc_review: str


class DriftEvent(BaseModel):
    schema_version: str = "layer1.drift_event.v1"
    event_type: str = "DRIFT_EVENT"
    event_id: str
    client_id: str
    client_name: str
    routing_hint: str = "layer2_structural_reasoning"
    severity: DriftSeverity
    drift_score: float = Field(ge=0.0, le=1.0)
    triggered_at: datetime = Field(default_factory=datetime.utcnow)
    matched_risk_terms: list[str]
    missing_baseline_terms: list[str]
    scoring_breakdown: dict[str, float] = Field(default_factory=dict)
    rationale: str
    recommended_action: str
    citations: list[dict[str, str]]
    loop_a_trace: dict[str, Any] = Field(default_factory=dict)
    source_metadata: dict[str, Any] = Field(default_factory=dict)
    layer1_cost_units: dict[str, float]


# ---------------------------------------------------------------------------
# HydraEngineOutput — exact schema of what the AI engine emits
# Field names and types match the colleague's output 1:1. Do not rename.
# ---------------------------------------------------------------------------

class HydraGraphChange(BaseModel):
    type: str                                  # "ADDED" | "DELETED" | "UNCHANGED"
    triple: str                                # "Entity A -> relation -> Entity B"


class HydraForecast(BaseModel):
    next_7_days_risk_trend: RiskTrend
    uncertainty: UncertaintyLevel


class HydraEngineOutput(BaseModel):
    """
    Exact schema produced by the HYDRA AI engine.
    Do not modify field names — they must match the engine output 1:1.
    Use .to_risk_alert() to convert into the enriched RiskAlert for the API.
    """
    client_id: str
    client_name: str
    event_type: str                            # e.g. "DRIFT_EVENT"
    drift_score: float                         # combined drift signal score (0–1)
    reconstruction_error: float                # raw VAE reconstruction loss
    threshold: float                           # dynamic VAE threshold at this moment
    risk_level: RiskLevel
    time_to_compliance_decay_days: float       # T from survival model
    router_decision: str                       # "HEAVY_REASONER" | "FAST_CLASSIFIER" | "DROPPED"
    reason: str                                # plain English explanation of the decision
    graph_changes: list[HydraGraphChange]      # Neo4j triple changes detected
    forecast: HydraForecast                    # TimeGPT output
    audit_citations: list[str]                 # citation IDs or source references
    recommended_action: str

    def to_risk_alert(self, alert_id: str) -> "RiskAlert":
        """Adapt raw engine output into the enriched RiskAlert consumed by API and frontend."""
        router_map = {
            "HEAVY_REASONER": RouterPath.HEAVY_REASONER,
            "FAST_CLASSIFIER": RouterPath.FAST_CLASSIFIER,
            "DROPPED": RouterPath.DROPPED,
        }
        loop_a = LoopATrace(
            vae_reconstruction_error=self.reconstruction_error,
            drift_threshold=self.threshold,
            drift_detected=self.event_type == "DRIFT_EVENT",
            drift_score=self.drift_score,
            top_keywords_matched=[],
            embedding_shift_score=self.drift_score,
            decision="DRIFT_EVENT emitted" if self.event_type == "DRIFT_EVENT" else "Signal dropped — stable",
        )
        graph_steps = [
            GraphRAGStep(
                entity=self.client_name,
                triple=gc.triple,
                triple_status=gc.type,
                relationship_change=gc.triple,
                cypher_query="",
                timestamp_slice="",
            )
            for gc in self.graph_changes
        ]
        loop_b = LoopBTrace(
            graph_steps=graph_steps,
            graph_summary=self.reason,
            timegpt_forecast_horizon_days=7,
            timegpt_anomaly_score=self.drift_score,
            timegpt_uncertainty_interval=(0.0, 0.0),
            timegpt_risk_trend=self.forecast.next_7_days_risk_trend,
            timegpt_uncertainty=self.forecast.uncertainty,
            timegpt_summary=f"Risk trend: {self.forecast.next_7_days_risk_trend.value}, uncertainty: {self.forecast.uncertainty.value}",
            survival_model_used="DeepSurv",
            time_to_compliance_decay_days=self.time_to_compliance_decay_days,
            survival_confidence=0.0,
            survival_summary=f"Compliance decay expected in {self.time_to_compliance_decay_days} days",
            router_path=router_map.get(self.router_decision, RouterPath.FAST_CLASSIFIER),
            router_decision=self.router_decision,
            router_reason=self.reason,
        )
        trace = AIReasoningTrace(
            trace_id=f"trace-{alert_id}",
            alert_id=alert_id,
            client_id=self.client_id,
            event_type=self.event_type,
            loop_a=loop_a,
            loop_b=loop_b,
            chain_of_thought=self.reason,
            audit_citations=[{"source": c} for c in self.audit_citations],
            guardrail_checks=[],
            bias_flags=[],
            hallucination_check_passed=True,
            total_tokens_used=0,
            total_cost_usd=0.0,
        )
        return RiskAlert(
            alert_id=alert_id,
            client_id=self.client_id,
            client_name=self.client_name,
            event_type=self.event_type,
            drift_score=self.drift_score,
            reconstruction_error=self.reconstruction_error,
            threshold=self.threshold,
            risk_score=min(self.drift_score * 10, 10.0),
            risk_level=self.risk_level,
            signal_type=self.event_type,
            explanation=self.reason,
            reason=self.reason,
            recommended_action=self.recommended_action,
            confidence=self.drift_score,
            time_to_compliance_decay_days=self.time_to_compliance_decay_days,
            router_decision=self.router_decision,
            graph_changes=self.graph_changes,
            forecast=self.forecast,
            audit_citations_raw=self.audit_citations,
            reasoning_trace=trace,
        )


# ---------------------------------------------------------------------------
# AI Reasoning Trace — step-by-step pipeline trace shown on the frontend
# ---------------------------------------------------------------------------

class LoopATrace(BaseModel):
    """Trace from HYDRA Loop A: High-Frequency Latent Regime Detection."""
    vae_reconstruction_error: float            # raw VAE loss (matches engine: reconstruction_error)
    drift_threshold: float                     # dynamic variance threshold (matches engine: threshold)
    drift_score: float                         # combined drift signal score (matches engine: drift_score)
    drift_detected: bool                       # True → DRIFT_EVENT emitted
    top_keywords_matched: list[str]            # high-risk keywords/entities that fired
    embedding_shift_score: float               # cosine distance from baseline latent centroid
    decision: str                              # "DRIFT_EVENT emitted" or "Signal dropped — stable"
    tokens_used: int = 0
    cost_usd: float = 0.0


class GraphRAGStep(BaseModel):
    """One Neo4j triple change detected during Loop B GraphRAG reasoning."""
    entity: str
    triple: str                                # "Entity A -> relation -> Entity B" (matches engine format)
    triple_status: str                         # "ADDED" | "DELETED" | "UNCHANGED" (matches engine: type)
    relationship_change: str                   # human-readable description
    cypher_query: str                          # the actual Neo4j query that ran
    timestamp_slice: str                       # time window this triple covers


class LoopBTrace(BaseModel):
    """Trace from HYDRA Loop B: Predictive GraphRAG & Deep Survival Inference."""
    model_config = ConfigDict(protected_namespaces=())

    # GraphRAG
    graph_steps: list[GraphRAGStep]
    graph_summary: str

    # TimeGPT forecasting
    timegpt_forecast_horizon_days: int
    timegpt_anomaly_score: float
    timegpt_uncertainty_interval: tuple[float, float]
    timegpt_risk_trend: RiskTrend              # matches engine: forecast.next_7_days_risk_trend
    timegpt_uncertainty: UncertaintyLevel      # matches engine: forecast.uncertainty
    timegpt_summary: str

    # Survival model
    survival_model_used: str                   # "SumoNet" | "DeepSurv" | "ConSurv"
    time_to_compliance_decay_days: float       # T — matches engine field name exactly
    survival_confidence: float
    survival_summary: str

    # Router decision
    router_path: RouterPath                    # our enum
    router_decision: str                       # raw string from engine: "HEAVY_REASONER" etc.
    router_reason: str                         # matches engine: reason

    # LLM (populated for fast/heavy paths)
    model_used: str | None = None
    tokens_used: int = 0
    cost_usd: float = 0.0


class AIReasoningTrace(BaseModel):
    """
    Complete step-by-step record of how HYDRA processed one signal.
    Primary model for the frontend explainability panel.
    Covers all engine output fields plus enriched frontend fields.
    """
    trace_id: str
    alert_id: str
    client_id: str
    event_type: str                            # matches engine: event_type

    loop_a: LoopATrace
    loop_b: LoopBTrace | None = None           # None if Loop A dropped the signal

    # Structured output from Outlines / Instructor
    chain_of_thought: str
    audit_citations: list[dict[str, str]]      # enriched: [{"source": ..., "url": ..., "excerpt": ...}]
    guardrail_checks: list[str]
    bias_flags: list[str]
    hallucination_check_passed: bool

    total_tokens_used: int
    total_cost_usd: float

    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Governance Record — compliance workflow trail shown on frontend
# ---------------------------------------------------------------------------

class GovernanceStep(BaseModel):
    step: str                                  # e.g. "Initial AI Flag", "Compliance Review"
    actor: str
    action: str
    outcome: str
    note: str = ""
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class GovernanceRecord(BaseModel):
    record_id: str
    alert_id: str
    client_id: str
    status: str                                # "pending" | "under_review" | "escalated" | "closed"
    steps: list[GovernanceStep]
    requires_manual_approval: bool
    approval_deadline: datetime | None = None
    final_decision: str | None = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# RiskAlert — unified model covering engine output + enriched frontend fields
# ---------------------------------------------------------------------------

class RiskAlert(BaseModel):
    alert_id: str
    client_id: str
    client_name: str = ""                      # from engine: client_name

    # Engine fields preserved verbatim
    event_type: str = ""                       # from engine: event_type
    drift_score: float = 0.0                   # from engine: drift_score
    reconstruction_error: float = 0.0          # from engine: reconstruction_error
    threshold: float = 0.0                     # from engine: threshold
    time_to_compliance_decay_days: float | None = None   # from engine
    router_decision: str = ""                  # from engine: router_decision ("HEAVY_REASONER" etc.)
    graph_changes: list[HydraGraphChange] = Field(default_factory=list)  # from engine
    forecast: HydraForecast | None = None      # from engine
    audit_citations_raw: list[str] = Field(default_factory=list)  # from engine (plain strings)
    reason: str = ""                           # from engine: reason

    # Enriched / computed fields for frontend
    risk_score: float = Field(default=0.0, ge=0.0, le=10.0)
    risk_level: RiskLevel = RiskLevel.LOW
    signal_type: str = ""
    explanation: str = ""
    recommended_action: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)

    # Originating raw signal from collectors
    raw_signal: RawSignal | None = None

    # KYC drift detection
    kyc_drift: KYCDriftRecord | None = None

    # Full AI reasoning trace for frontend explainability panel
    reasoning_trace: AIReasoningTrace | None = None

    # Compliance governance workflow
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
    model_config = ConfigDict(protected_namespaces=())

    stage: str                                 # "loop_a" | "loop_b_fast" | "loop_b_heavy"
    model_used: str
    tokens_used: int
    estimated_cost_usd: float
    calls: int
    cost_per_1000_analyses_usd: float
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class CostSummary(BaseModel):
    total_signals_processed: int
    total_dropped_by_loop_a: int
    total_escalated_to_loop_b: int
    total_tokens_used: int
    total_cost_usd: float
    cost_per_1000_analyses_usd: float
    breakdown: list[CostTracker]
    as_of: datetime = Field(default_factory=datetime.utcnow)
