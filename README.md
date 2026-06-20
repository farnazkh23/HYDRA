# SwissHacks HYDRA — Risk Intelligence Platform

**AMINA Bank Challenge: Dynamic Risk Profiling System (Real-Time Intelligence)**

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        PUBLIC DATA SOURCES                          │
│  NewsAPI · OpenSanctions · WHOIS · OpenCorporates · GLEIF · GDELT  │
└────────────────────────────┬────────────────────────────────────────┘
                             │ RawSignal events
                             ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       BACKEND  (FastAPI)                            │
│                                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐   │
│  │  Collectors  │  │  KYC Store   │  │      Scheduler         │   │
│  │  news.py     │  │  profiles/   │  │  APScheduler           │   │
│  │  sanctions   │─▶│  (baselines) │  │  polls sources /5 min  │   │
│  │  domain.py   │  └──────────────┘  └────────────────────────┘   │
│  └──────┬───────┘                                                   │
│         │                                                           │
│         ▼                                                           │
│  ┌─────────────────────────────────────┐  ┌─────────────────────┐ │
│  │         REST API (FastAPI)          │  │    Alert Store      │ │
│  │  GET  /clients                      │◀─│    (SQLite)         │ │
│  │  GET  /clients/{id}/alerts          │  │  alerts             │ │
│  │  GET  /clients/{id}/risk            │  │  reasoning traces   │ │
│  │  GET  /clients/{id}/kyc-drift       │  │  governance records │ │
│  │  GET  /alerts/{id}/trace            │  │  audit log          │ │
│  │  GET  /alerts/{id}/governance       │  └─────────────────────┘ │
│  │  POST /alerts/{id}/action           │                           │
│  │  GET  /audit-log                    │                           │
│  │  GET  /cost-summary                 │                           │
│  └────────────────┬────────────────────┘                           │
└───────────────────┼─────────────────────────────────────────────────┘
                    │ RawSignal stream
                    ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       HYDRA AI ENGINE                               │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LOOP A — High-Frequency Latent Regime Detection             │  │
│  │                                                              │  │
│  │  SPLADE + ONNX Transformer (hybrid sparse/dense embedding)   │  │
│  │       ↓                                                      │  │
│  │  VAE Reconstruction Error vs dynamic variance threshold      │  │
│  │       ↓                                                      │  │
│  │  LoopATrace emitted: {vae_error, threshold, keywords,        │  │
│  │                        embedding_shift, decision}            │  │
│  │       ↓                          ↓                           │  │
│  │  DRIFT_EVENT →              Signal DROPPED (stable)          │  │
│  └──────────┬───────────────────────────────────────────────────┘  │
│             │ DRIFT_EVENT + LoopATrace                              │
│             ▼                                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LOOP B — Predictive GraphRAG & Deep Survival Inference      │  │
│  │                                                              │  │
│  │  Neo4j Temporal GraphRAG                                     │  │
│  │    LLM triple-resolution → {added, deleted, unchanged}       │  │
│  │    GraphRAGStep[] emitted per entity relationship change     │  │
│  │       ↓                                                      │  │
│  │  Nixtla TimeGPT zero-shot forecasting                        │  │
│  │    anomaly score + uncertainty interval emitted              │  │
│  │       ↓                                                      │  │
│  │  Deep Survival Network (SumoNet / DeepSurv / ConSurv)       │  │
│  │    S(t|X) survival curve → Time-to-Compliance-Decay T        │  │
│  │       ↓                                                      │  │
│  │  Cascading Router                                            │  │
│  │    T ≥ 7 days  →  FAST classifier (lightweight model)        │  │
│  │    T < 7 days  →  HEAVY reasoner (DeepSeek-R1)              │  │
│  │       ↓                                                      │  │
│  │  Outlines / Instructor structured generation                 │  │
│  │    forces: chain_of_thought + audit_citations + risk token   │  │
│  │       ↓                                                      │  │
│  │  LoopBTrace + AIReasoningTrace emitted                       │  │
│  └──────────────────────┬───────────────────────────────────────┘  │
└─────────────────────────┼───────────────────────────────────────────┘
                          │ RiskAlert (with full AIReasoningTrace
                          │            + GovernanceRecord embedded)
                          ▼
┌─────────────────────────────────────────────────────────────────────┐
│                       FRONTEND  (React)                             │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  CLIENT OVERVIEW                                           │    │
│  │  Risk score · KYC baseline · drift status · open alerts    │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  ALERT FEED                                                │    │
│  │  Signal type · source · confidence · recommended action    │    │
│  │  [ Approve ]  [ Escalate ]  [ Dismiss ]                   │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  AI REASONING PANEL  (per alert — full trace)              │    │
│  │                                                            │    │
│  │  ① Loop A:  VAE error 0.83 > threshold 0.41 → DRIFT       │    │
│  │             Keywords matched: [sanction, fraud]            │    │
│  │             Embedding shift: 0.74 from baseline            │    │
│  │                                                            │    │
│  │  ② GraphRAG: beneficial_owner "John Doe" → ADDED          │    │
│  │              jurisdiction "CH" → "KY" CHANGED             │    │
│  │                                                            │    │
│  │  ③ TimeGPT:  tx volume +340% projected in 5 days          │    │
│  │              uncertainty: [2.1×, 4.8×]                    │    │
│  │                                                            │    │
│  │  ④ Survival: T = 3.2 days → HEAVY reasoner triggered      │    │
│  │                                                            │    │
│  │  ⑤ DeepSeek-R1 chain-of-thought + cited sources           │    │
│  │     Guardrail checks ✓  Hallucination check ✓             │    │
│  └────────────────────────────────────────────────────────────┘    │
│                                                                     │
│  ┌───────────────────────┐  ┌─────────────────────────────────┐   │
│  │  KYC DRIFT VIEWER     │  │  GOVERNANCE TRAIL               │   │
│  │  Baseline vs current  │  │  Step-by-step compliance flow   │   │
│  │  field-by-field diff  │  │  who acted · when · outcome     │   │
│  │  Re-KYC flag          │  │  approval status · deadline     │   │
│  └───────────────────────┘  └─────────────────────────────────┘   │
│                                                                     │
│  ┌────────────────────────────────────────────────────────────┐    │
│  │  COST TRACKER                                              │    │
│  │  Signals processed · dropped by Loop A · escalated        │    │
│  │  Tokens per stage · $ per stage · cost/1000 analyses      │    │
│  └────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
SwissHacksHYDRA/
│
├── frontend/                        # React dashboard
│   └── (React app — TBD)
│
├── backend/                         # FastAPI backend
│   ├── collectors/
│   │   ├── news.py                  # Event Registry / News MCP → RawSignal events
│   │   ├── sanctions.py             # OpenSanctions → entity screening
│   │   └── domain.py               # WHOIS → domain change detection
│   ├── kyc/
│   │   └── profiles.json           # Simulated KYC baseline profiles
│   ├── api.py                       # FastAPI routes
│   ├── scheduler.py                 # APScheduler polling loop
│   ├── models.py                    # All Pydantic schemas (shared contract)
│   └── db.py                        # SQLite store
│
├── stream_engine/                   # LOOP A — Regime Detection (AI)
│   ├── vectorizer.py
│   └── drift_engine.py
│
├── analytic_engine/                 # LOOP B — Deep Inference (AI)
│   ├── graph_fusion.py
│   ├── time_series.py
│   ├── datasets.py
│   ├── models.py
│   └── router.py
│
├── main.py                          # Async event-driven entrypoint
└── README.md
```

---

## Shared Data Contracts

All schemas live in `backend/models.py` and are the contract between the AI engine, the backend API, and the frontend.

### RawSignal — backend → HYDRA engine

```json
{
  "entity_name": "Binance",
  "client_id": "client_001",
  "signal_type": "news",
  "source": "event_registry",
  "content": "Binance executive arrested on money laundering charges...",
  "timestamp": "2026-06-19T10:00:00Z",
  "metadata": { "url": "...", "author": "Reuters" }
}
```

### AIReasoningTrace — HYDRA engine → backend → frontend explainability panel

```json
{
  "trace_id": "trace_abc123",
  "alert_id": "alert_001",
  "loop_a": {
    "vae_reconstruction_error": 0.83,
    "drift_threshold": 0.41,
    "drift_detected": true,
    "top_keywords_matched": ["sanction", "arrest", "fraud"],
    "embedding_shift_score": 0.74,
    "decision": "DRIFT_EVENT emitted",
    "tokens_used": 0,
    "cost_usd": 0.0
  },
  "loop_b": {
    "graph_steps": [
      {
        "entity": "Binance Holdings Ltd",
        "relationship_change": "new beneficial owner added",
        "triple_status": "added",
        "cypher_query": "MATCH (e:Entity {name: 'Binance'}) ...",
        "timestamp_slice": "2026-06-01 to 2026-06-19"
      }
    ],
    "timegpt_forecast_horizon_days": 7,
    "timegpt_anomaly_score": 0.91,
    "timegpt_uncertainty_interval": [2.1, 4.8],
    "timegpt_summary": "Transaction volume projected to spike 3× in 5 days",
    "survival_model_used": "SumoNet",
    "time_to_decay_days": 3.2,
    "survival_confidence": 0.88,
    "survival_summary": "KYC compliance expected to decay in 3.2 days",
    "router_path": "heavy",
    "router_reason": "T=3.2 days < 7-day threshold",
    "model_used": "deepseek-r1",
    "tokens_used": 4800,
    "cost_usd": 0.0048
  },
  "chain_of_thought": "Step 1: Signal received about Binance arrest...",
  "audit_citations": [
    { "url": "https://...", "excerpt": "Executive arrested...", "source": "Reuters" }
  ],
  "guardrail_checks": ["no hallucinated entities", "all citations verified", "no PII leaked"],
  "hallucination_check_passed": true,
  "total_tokens_used": 4800,
  "total_cost_usd": 0.0048
}
```

### GovernanceRecord — compliance workflow trail shown on frontend

```json
{
  "record_id": "gov_001",
  "alert_id": "alert_001",
  "status": "under_review",
  "steps": [
    {
      "step": "Initial AI Flag",
      "actor": "HYDRA Engine",
      "action": "Risk alert generated",
      "outcome": "Routed to compliance queue",
      "timestamp": "2026-06-19T10:05:00Z"
    },
    {
      "step": "Compliance Review",
      "actor": "compliance_officer",
      "action": "Reviewed alert and reasoning trace",
      "outcome": "Escalated to senior risk officer",
      "timestamp": "2026-06-19T10:30:00Z"
    }
  ],
  "requires_manual_approval": true,
  "approval_deadline": "2026-06-20T10:00:00Z",
  "final_decision": null
}
```

### KYCDriftRecord — field-level diff shown in KYC drift viewer

```json
{
  "client_id": "client_001",
  "overall_drift_severity": "HIGH",
  "rekyc_required": true,
  "summary": "Jurisdiction changed from CH to KY; new beneficial owner detected",
  "drifted_fields": [
    {
      "field": "jurisdiction",
      "baseline_value": "CH",
      "current_value": "KY",
      "drift_severity": "HIGH",
      "source": "OpenCorporates"
    },
    {
      "field": "beneficial_owners",
      "baseline_value": "Jane Smith",
      "current_value": "Jane Smith, Unknown Entity Ltd",
      "drift_severity": "CRITICAL",
      "source": "GLEIF"
    }
  ]
}
```

---

## Frontend Views

| View | Data source | Purpose |
|---|---|---|
| Client Overview | `ClientRiskSummary` | Risk score, drift flag, open alert count |
| Alert Feed | `RiskAlert` | Live alerts with confidence + recommended action |
| AI Reasoning Panel | `AIReasoningTrace` | Step-by-step Loop A → Loop B → LLM trace |
| KYC Drift Viewer | `KYCDriftRecord` | Baseline vs current, field-by-field diff |
| Governance Trail | `GovernanceRecord` | Who acted, when, outcome, approval status |
| Audit Log | `AlertActionRecord` | Full immutable action history |
| Cost Tracker | `CostSummary` | Tokens/stage, $/stage, cost per 1000 analyses |

---

## Backend API Endpoints

| Method | Endpoint | Returns |
|---|---|---|
| GET | `/clients` | `list[ClientRiskSummary]` |
| GET | `/clients/{id}/alerts` | `list[RiskAlert]` |
| GET | `/clients/{id}/risk` | `ClientRiskSummary` |
| GET | `/clients/{id}/kyc-drift` | `KYCDriftRecord` |
| GET | `/alerts/{id}/trace` | `AIReasoningTrace` |
| GET | `/alerts/{id}/governance` | `GovernanceRecord` |
| POST | `/alerts/{id}/action` | `AlertActionRecord` |
| GET | `/audit-log` | `list[AlertActionRecord]` |
| GET | `/cost-summary` | `CostSummary` |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + TailwindCSS |
| Backend API | Python · FastAPI |
| Scheduling | APScheduler |
| Database | SQLite (alerts, traces, governance, audit log) |
| AI Engine — Loop A | SPLADE · ONNX · VAE |
| AI Engine — Loop B | Neo4j · TimeGPT · DeepSurv/SumoNet · DeepSeek-R1 |
| Structured Generation | Outlines / Instructor (Pydantic-enforced output) |
| Data Sources | NewsAPI · OpenSanctions · WHOIS · OpenCorporates · GLEIF |

---

## Judging Criteria

| Criterion | Weight | Our Approach |
|---|---|---|
| AI Intelligence Quality | 25% | HYDRA dual-loop: VAE drift detection + GraphRAG + survival inference |
| Cost Efficiency | 20% | Loop A drops stable signals for free; Loop B routes to heavy LLM only when T < 7 days. Cost tracked per stage with cost/1000 analyses. |
| UX & Explainability | 20% | AI Reasoning Panel shows every step of the pipeline. KYC Drift Viewer shows field-level diffs. All AI output includes confidence scores + cited sources. |
| Compliance & Safety | 20% | Human-in-the-loop governance workflow. Hallucination checks. Guardrail validation. Pydantic-enforced structured output. Immutable audit log. |
| Engineering & Architecture | 15% | Modular pipeline, shared Pydantic schemas, async event-driven main loop, clean separation of data layers. |
