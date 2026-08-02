export type RiskStatus = "low" | "medium" | "elevated" | "high";
export type DriftSeverity = "low" | "medium" | "high" | "critical";

export interface Customer {
  id: string;
  companyName: string;
  legalName: string;
  responsiblePerson: string;
  responsiblePersonRole: string;
  industry: string;
  country: string;
  onboardedDate: string;
  kycStatus: "Verified" | "Pending" | "Incomplete";
  riskStatus: RiskStatus;
  riskScore: number;
  driftPercent: number;
  driftSeverity: DriftSeverity;
  lastUpdated: string;
  transactionVolume: string;
  companyType: string;
  isNewlyOnboarded?: boolean;
  profileBuildingStatus?: string;
  trend: "up" | "down" | "flat";
}

export interface Citation {
  title?: string;
  url?: string;
  published_at?: string;
  source?: string;
  provider?: string;
  query?: string;
  matched_risk_terms?: string[];
  reason?: string;
}

export interface Alert {
  id: string;
  customerId: string;
  customerName: string;
  title: string;
  severity: "medium" | "elevated" | "high";
  driftType: string;
  timestamp: string;
  explanation: string;
  status: "open" | "investigating" | "dismissed";
  // Backend-enriched fields; absent on the static mock fallback.
  matchedRiskTerms?: string[];
  missingBaselineTerms?: string[];
  driftScore?: number;
  recommendedAction?: string;
  citations?: Citation[];
  reasoningTrace?: AIReasoningTrace | null;
  governance?: GovernanceRecord | null;
}

export interface GraphNode {
  id: string;
  label: string;
  type: "company" | "person" | "jurisdiction" | "unknown";
  riskStatus: RiskStatus;
  driftScore: number;
  lastUpdated: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  relationship: string;
  isNewlyDetected?: boolean;
  severity?: RiskStatus;
}

export interface RawSignal {
  entity_name: string;
  client_id: string;
  signal_type: string;
  source: string;
  content: string;
  timestamp: string;
  metadata: Record<string, unknown>;
}

export interface AIReasoningTrace {
  trace_id: string;
  alert_id: string;
  loop_a: {
    vae_reconstruction_error: number;
    drift_threshold: number;
    drift_detected: boolean;
    top_keywords: string[];
    embedding_shift_score: number;
    decision: string;
    cost_usd: number;
  };
  loop_b: {
    graphrag: { triple_status: string; new_entity: string; timestamp_slice: string } | null;
    timegpt: { horizon_days: number; anomaly_score: number; uncertainty: [number, number]; summary: string };
    survival: { model: string; time_to_decay_days: number; confidence: number; summary: string };
    router: { path: string; reason: string; model: string; tokens: number; cost_usd: number };
  } | null;
  audit_citations: string[];
  guardrail_checks: string[];
  hallucination_check_passed: boolean;
  total_tokens_used: number;
  total_cost_usd: number;
  decision_rationale: string;
}

export interface KYCDriftRecord {
  client_id: string;
  overall_drift_severity: RiskStatus;
  rekyc_required: boolean;
  summary: string;
  drifted_fields: Array<{
    field: string;
    baseline_value: string;
    current_value: string;
    drift_severity: RiskStatus;
    source: string;
  }>;
}

export interface GovernanceRecord {
  record_id: string;
  alert_id: string;
  status: string;
  steps: string[];
  requires_manual_approval: boolean;
  approval_deadline: string;
  final_decision: string;
}
