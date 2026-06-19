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


# ---------------------------------------------------------------------------
# KYC Profile — simulated internal bank data
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
    onboarding_date: str                       # when the bank onboarded them
    website: str
    notes: str = ""


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
# RiskAlert — produced by HYDRA analytic_engine, consumed by API + frontend
# ---------------------------------------------------------------------------

class RiskAlert(BaseModel):
    alert_id: str
    client_id: str
    risk_score: float = Field(ge=0.0, le=10.0)
    risk_level: RiskLevel
    signal_type: str                           # human-readable flag label
    explanation: str                           # plain English summary
    confidence: float = Field(ge=0.0, le=1.0)
    time_to_decay_days: float | None = None    # T from survival model
    audit_citations: list[str] = Field(default_factory=list)
    chain_of_thought: str = ""
    recommended_action: str = ""
    raw_signal: RawSignal | None = None        # originating signal
    timestamp: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# AlertActionRecord — written to audit log when a user acts on an alert
# ---------------------------------------------------------------------------

class AlertActionRecord(BaseModel):
    record_id: str
    alert_id: str
    client_id: str
    action: AlertAction
    actor: str = "compliance_officer"          # role or user ID
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
    last_updated: datetime | None


class CostTracker(BaseModel):
    stage: str                                 # "loop_a", "loop_b_fast", "loop_b_heavy"
    tokens_used: int
    estimated_cost_usd: float
    calls: int
    timestamp: datetime = Field(default_factory=datetime.utcnow)
