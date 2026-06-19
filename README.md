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
│                     BACKEND  (FastAPI)                              │
│                                                                     │
│  ┌─────────────┐   ┌──────────────┐   ┌──────────────────────────┐ │
│  │  Collectors │   │  KYC Store   │   │       Scheduler          │ │
│  │  news.py    │   │  profiles/   │   │  APScheduler / cron      │ │
│  │  sanctions  │──▶│  (baseline   │   │  polls sources every 5m  │ │
│  │  domain.py  │   │   profiles)  │   └──────────────────────────┘ │
│  └──────┬──────┘   └──────┬───────┘                                │
│         │                 │                                         │
│         ▼                 ▼                                         │
│  ┌─────────────────────────────────┐   ┌──────────────────────┐   │
│  │         REST API (FastAPI)      │   │      Alert Store      │   │
│  │  GET  /clients                  │◀──│      (SQLite)         │   │
│  │  GET  /clients/{id}/alerts      │   │  alerts, audit log,   │   │
│  │  GET  /clients/{id}/risk        │   │  action history       │   │
│  │  POST /alerts/{id}/action       │   └──────────────────────┘   │
│  │  GET  /audit-log                │                               │
│  └───────────────┬─────────────────┘                               │
└──────────────────┼──────────────────────────────────────────────────┘
                   │ RawSignal stream
                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    HYDRA AI ENGINE                                  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LOOP A — High-Frequency Latent Regime Detection             │  │
│  │  SPLADE + ONNX Transformer → VAE Reconstruction Error        │  │
│  │  Regime-Shift Gate → emits DRIFT_EVENT or drops signal       │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
│                             │ DRIFT_EVENT                           │
│                             ▼                                       │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  LOOP B — Predictive GraphRAG & Deep Survival Inference      │  │
│  │  Neo4j Temporal GraphRAG → TimeGPT forecasting               │  │
│  │  Deep Survival Network → Time-to-Compliance-Decay (T)        │  │
│  │  Cascading Router: T≥7d → fast classifier / T<7d → DeepSeek │  │
│  │  Outlines structured generation → RiskAlert (Pydantic)       │  │
│  └──────────────────────────┬───────────────────────────────────┘  │
└──────────────────────────────┼──────────────────────────────────────┘
                               │ RiskAlert JSON
                               ▼
┌─────────────────────────────────────────────────────────────────────┐
│                     FRONTEND  (React)                               │
│                                                                     │
│  ┌──────────────┐  ┌─────────────────┐  ┌───────────────────────┐  │
│  │ Client Cards │  │   Alert Feed    │  │   Audit Log / Actions │  │
│  │ risk score   │  │ signal · source │  │ Approve · Escalate    │  │
│  │ drift status │  │ explanation     │  │ Dismiss · timestamp   │  │
│  │ KYC baseline │  │ confidence      │  │                       │  │
│  └──────────────┘  └─────────────────┘  └───────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Cost Tracker — tokens used per stage · estimated $ spend    │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Repository Structure

```
SwissHacksHYDRA/
│
├── frontend/                        # React dashboard (UI)
│   └── (React app — TBD)
│
├── backend/                         # FastAPI backend
│   ├── collectors/
│   │   ├── news.py                  # NewsAPI → RawSignal events
│   │   ├── sanctions.py             # OpenSanctions → entity screening
│   │   └── domain.py               # WHOIS → domain change detection
│   ├── kyc/
│   │   └── profiles.json           # Simulated KYC baseline profiles
│   ├── api.py                       # FastAPI routes
│   ├── scheduler.py                 # APScheduler polling loop
│   ├── models.py                    # Shared Pydantic schemas
│   └── db.py                        # SQLite alert store
│
├── stream_engine/                   # LOOP A — Regime Detection (AI)
│   ├── ingestion.py
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
├── config/
│   └── baselines_all.yaml
│
├── main.py                          # Async event-driven entrypoint
└── README.md
```

---

## Shared Data Contracts

### RawSignal — produced by backend, consumed by HYDRA engine

```json
{
  "entity_name": "Binance",
  "signal_type": "news | sanction | domain_change | registry",
  "source": "NewsAPI",
  "content": "raw text or summary",
  "timestamp": "2026-06-19T10:00:00Z",
  "metadata": { "url": "...", "author": "..." }
}
```

### RiskAlert — produced by HYDRA engine, consumed by backend API + frontend

```json
{
  "client_id": "client_001",
  "risk_score": 8.4,
  "risk_level": "HIGH",
  "signal_type": "Reputational Risk",
  "explanation": "Human-readable summary of the flag",
  "confidence": 0.91,
  "time_to_decay_days": 3,
  "audit_citations": ["source_url_1", "source_url_2"],
  "chain_of_thought": "Step-by-step reasoning...",
  "recommended_action": "Trigger enhanced due diligence",
  "timestamp": "2026-06-19T10:05:00Z"
}
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React + TailwindCSS |
| Backend API | Python · FastAPI |
| Scheduling | APScheduler |
| Database | SQLite (alerts, audit log) |
| AI Engine — Loop A | SPLADE · ONNX · VAE |
| AI Engine — Loop B | Neo4j · TimeGPT · DeepSurv · DeepSeek-R1 |
| Structured Generation | Outlines / Instructor |
| Data Sources | NewsAPI · OpenSanctions · WHOIS · OpenCorporates |

---

## Judging Criteria (AMINA Bank)

| Criterion | Weight | Our Approach |
|---|---|---|
| AI Intelligence Quality | 25% | HYDRA dual-loop with GraphRAG + survival inference |
| Cost Efficiency | 20% | 3-stage cascade: rules → small model → heavy LLM only when T<7d |
| UX & Explainability | 20% | React dashboard with confidence scores + chain-of-thought |
| Compliance & Safety | 20% | Human-in-the-loop actions, audit log, Pydantic-enforced output |
| Engineering & Architecture | 15% | Modular pipeline, shared schemas, async event-driven main loop |
