# Layer 2: Deep Multi-Modal Telemetry & Sovereign Reasoning Engine

Layer 2 is the deep analytical core of the HYDRA risk architecture. While Layer 1 operates as a sub-millisecond, low-cost edge firewall to drop public signal noise (saving nominal signal snapshots to a local VAE buffer), Layer 2 serves as an **event-driven orchestration engine**. It triggers downstream execution loops only when Layer 1 emits a structured `DRIFT_EVENT` payload contract.

It fuses real-time time-series volumetrics, topological graph state mutations, and neural survival modeling to generate sovereign, audit-ready compliance reports.

---

## 🏗️ Architectural Workflow & Components

Once a `DRIFT_EVENT` crosses the threshold from Layer 1, Layer 2 executes the following synchronized sequence:

```
    [ LAYER 1 DRIFT_EVENT PAYLOAD ]
                   │
                   ▼
┌──────────────────────────────────────┐
│ 1. Graph Topology Inversion          │ ──► Maps entity roles/hints to live Neo4j Aura Cloud
└──────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ 2. Volumetric Anomaly Detection      │ ──► Validates cash flows via Nixtla TimeGPT
└──────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ 3. Multi-Modal Imputation Matrix     │ ──► Vectorizes unified features into PyTorch Tensors
└──────────────────────────────────────┘
                   │
                   ▼
┌──────────────────────────────────────┐
│ 4. Neural Deep Survival Model        │ ──► Computes Hazard Runway Horizon (T)
└──────────────────────────────────────┘
                   │
                   ▼  (If T < 7.0 Days)
┌──────────────────────────────────────┐
│ 5. Sovereign Guardrailed Router      │ ──► Escalates to Swiss Apertus AI (CSCS Alps)
└──────────────────────────────────────┘

```

### 1. Graph Topology Inversion (`analytic_engine/graph_fusion.py`)

* **Role:** GraphRAG Contextualization & Baseline Mutation.
* **Mechanism:** Consumes the stable Layer 1 `source_metadata` block (`relationship_hints`, `entity_roles`). It programmatically builds parameterized Cypher queries to inject newly discovered counterparty nodes and mutate historical client KYC baselines inside a **live Neo4j Aura Cloud** instance.

### 2. Volumetric Anomaly Detection (`analytic_engine/time_series.py`)

* **Role:** Internal Financial Verification Gate.
* **Mechanism:** Queries transaction ledger histories using the **Nixtla TimeGPT API** to cross-examine public sentiment shifts against internal transactional velocity, flagging material structural behavior anomalies (e.g., catching sudden multi-million CHF transaction spikes breaking long dormancy periods).

### 3. Neural Deep Survival Modeling (`analytic_engine/models.py`)

* **Role:** Predictive Risk Horizon Quantification.
* **Mechanism:** Aggregates time-series variances and topological graph changes into a unified **PyTorch continuous feature matrix**. A Deep Survival Model calculates an active hazard function to determine the **Survival Horizon Time ($T$)**—predicting exactly how many days remain before a critical regulatory baseline breach collapses the account status.

### 4. Cost-Aware Guardrailed Router (`analytic_engine/router.py`)

* **Role:** Sovereign Reasoning & Budget Enforcement.
* **Mechanism:** If $T \ge 7.0$ days, the engine bypasses heavy compute costs, records an automated tracking pass, and logs low-tier metric budgets. If $T < 7.0$ days, it flags a **Critical Drift Breach**, escalates token tiers, and routes the context payload straight to the **Sovereign Swiss Apertus AI Engine**.

---

## 🇨🇭 Sovereign Tech Stack & Data Protection

Layer 2 is uniquely engineered to fulfill strict data sovereignty requirements, ensuring confidential internal institutional profiling data never leaks to non-compliant third-party cloud frameworks:

* **Sovereign AI Infrastructure:** Integrates natively with the **Swiss AI Initiative's Apertus LLM (`swiss-ai/apertus-8b-instruct`)** via the PublicAI gateway. Invocations run entirely on **CSCS (Swiss National Supercomputing Centre)** infrastructure powered by the "Alps" supercomputer cluster.
* **Localized Contextual Audits:** The inference pipeline dynamically prompts the model to inject specific Swiss regulatory frameworks—producing definitive audit trails citing **FINMA anti-money laundering (AML)** guidelines, **ZEFIX** registry changes, and federal cybersecurity baselines.
* **Fault-Tolerant Network Isolation:** Equipped with an automatic `Pydantic`-validated structural recovery loop. If a remote cloud handshake experiences an infrastructure timeout or a `401 Unauthorized` token block on stage, Layer 2 intercepts the exception gracefully, prevents an application crash, merges live data source URLs, and logs an isolated fallback survival state.

---

## 📈 Definitive Output Schema Contract

Every integrated execution loop culminates in an immutable, audit-ready compliance ledger output tracking the exact telemetry lineage back to the originating live public news signal:

```json
================== DEFINITIVE AUDIT LOG OUTPUT ==================
Risk Rating Token : CRITICAL_BREACH
Compliance Audit  : Client SpaceX's profile update confirms a business purpose change... [FINMA AML Analysis text synthesized by Apertus 8B]
Source Citations  : ['https://www.yahoo.com/news/science/articles/spacex-conducting-third-mishap-investigation...', 'Internal Transaction Ledger Match', 'Swiss Corporate Registry (ZEFIX) Fallback Check']
Pipeline Budget   : {'cheap_tier_calls': 0, 'heavy_tier_calls': 1, 'total_cost_usd': 0.00015}
=================================================================

```

---

## 🚀Other Advantages

* **Defensive Cost Optimization:** Gating heavy LLM calls behind lightweight numerical tracking engines means the system costs near **\$0.00** during nominal operations. It only flags heavy-reasoning billing units (**$0.00015 USD**) when an account undergoes a mathematically verified emergency.
* **GraphRAG Precision:** Rather than feeding noisy, raw histories into an LLM context window, Layer 2 leverages structured graph topology to pass deterministic relational mutations—drastically increasing audit log accuracy.
* **True Data Sovereignty:** Ideal for Swiss compliance regulations; financial risk profiles are processed, reasoned over, and logged entirely on sovereign Swiss supercomputing infrastructure.