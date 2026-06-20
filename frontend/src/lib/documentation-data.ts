export type DocLayer = 1 | 2 | "bridge" | "input" | "output";

export type DocNode = {
  id: string;
  layer: DocLayer;
  title: string;
  short: string;
  role: string;
  consumes: string;
  produces: string;
  why: string;
};

export const publicInputNode: DocNode = {
  id: "public-intelligence",
  layer: "input",
  title: "Public Intelligence",
  short: "OSINT · News · Registry Data · Monitored Entity References",
  role: "Cheap, high-volume external signal surface ingested into Layer 1.",
  consumes: "Open web, OSINT feeds, public registries, monitored entity lists.",
  produces: "Raw public payloads forwarded to the Layer 1 normalizer.",
  why: "Defines the universe of low-cost signals HYDRA can observe before any reasoning cost is incurred.",
};

export const internalInputNode: DocNode = {
  id: "internal-banking",
  layer: "input",
  title: "Internal Banking Data",
  short: "Transaction Ledger · Cash-Flow Velocity · Volume History · Dormancy Patterns",
  role: "Privileged internal series used by Layer 2 to confirm materiality of drift.",
  consumes: "Core banking ledger, transaction velocity, dormancy and volume histories.",
  produces: "Time-series feeds consumed by Volumetric Anomaly Detection (TimeGPT).",
  why: "Public signals alone cannot prove behavioural change — internal flows validate whether a drift is materially real.",
};

// kept for backwards compatibility with existing imports
export const inputNode: DocNode = publicInputNode;

export const layer1Meta: DocNode = {
  id: "layer-1",
  layer: 1,
  title: "Layer 1 — Local Edge Firewall (Low-Cost Public Intelligence Gate)",
  short:
    "Local edge firewall: normalizes raw public signals, drops stable noise cheaply, emits DRIFT_EVENT only when reconstruction error crosses threshold.",
  role: "Low-cost drift gate running entirely on the local edge.",
  consumes: "Raw public signals and KYC baseline profiles.",
  produces: "DRIFT_EVENT payloads or stable VAE snapshots.",
  why: "Most signals are stable and can be dropped locally before any cloud or LLM cost is incurred.",
};

export const layer1Nodes: DocNode[] = [
  {
    id: "kyc-baseline-loader",
    layer: 1,
    title: "KYC Baseline Loader",
    short: "Loads the live KYC baseline for every monitored entity.",
    role: "Hydrates the per-client KYC reference used by the drift gate.",
    consumes: "KYC baseline profiles + monitored entity references.",
    produces: "In-memory baseline state available to downstream components.",
    why: "Drift can only be measured against a current, per-client baseline.",
  },
  {
    id: "raw-signal-normalizer",
    layer: 1,
    title: "RawSignal Normalizer",
    short: "Cleans and canonicalizes raw OSINT and news payloads.",
    role: "Parses, dedupes, and standardizes incoming public payloads.",
    consumes: "Raw OSINT, news, registry payloads.",
    produces: "Normalized signal records with stable schema.",
    why: "Downstream gates require a typed, deduped input to score reliably.",
  },
  {
    id: "relevance-gate",
    layer: 1,
    title: "Relevance Gate",
    short: "Discards signals unrelated to any monitored entity.",
    role: "First coarse filter — entity matching against monitored list.",
    consumes: "Normalized signals + monitored entity references.",
    produces: "Entity-relevant signal subset.",
    why: "Removes the majority of the firehose before any encoding cost.",
  },
  {
    id: "sparse-dense-encoder",
    layer: 1,
    title: "Sparse + Dense Encoder",
    short: "Hybrid TF-IDF / hash + dense embedding representation.",
    role: "Encodes relevant signals into the feature space the VAE consumes.",
    consumes: "Entity-relevant signals.",
    produces: "Sparse + dense feature vectors.",
    why: "Hybrid encoding is robust to vocabulary drift and works under the ONNX fallback path.",
  },
  {
    id: "vae-drift-gate",
    layer: 1,
    title: "Lightweight VAE Drift Gate",
    short: "Reconstructs encoded signal; reconstruction error = drift score.",
    role: "Cheap local drift detector — no LLM tokens, no cloud calls.",
    consumes: "Sparse + dense feature vectors + per-client baseline.",
    produces: "Drift score and stable/suspicious verdict.",
    why: "Local VAE keeps nominal screening at $0.00 cloud fees and 0 LLM tokens.",
  },
  {
    id: "stable-snapshot-buffer",
    layer: 1,
    title: "Stable Snapshot Buffer",
    short: "Persists nominal VAE snapshots for stable clients.",
    role: "Long-term store of nominal baselines for replay and audit.",
    consumes: "Stable verdicts from the drift gate.",
    produces: "Append-only snapshot history per client.",
    why: "Enables replay mode and proves nominal status to auditors without re-running reasoning.",
  },
  {
    id: "drift-event-emitter",
    layer: 1,
    title: "DRIFT_EVENT Emitter",
    short: "Wraps suspicious drift into a typed DRIFT_EVENT payload.",
    role: "The only component allowed to wake Layer 2.",
    consumes: "Suspicious verdicts + drift context.",
    produces: "DRIFT_EVENT payload with severity, score, routing hint, citations.",
    why: "Layer 2 is event-driven — no emitter, no expensive reasoning.",
  },
];

export const bridgeNode: DocNode = {
  id: "drift-event",
  layer: "bridge",
  title: "DRIFT_EVENT Payload",
  short: "The single contract that wakes Layer 2.",
  role: "Event envelope produced by Layer 1, consumed by Layer 2.",
  consumes: "Output of the DRIFT_EVENT Emitter.",
  produces: "Typed event consumed by the Sovereign Reasoning Engine.",
  why: "Layer 2 is event-driven — it never runs without this payload, which keeps cost near zero in steady state.",
};

export const bridgeFields: { k: string; v: string }[] = [
  { k: "event_type", v: "DRIFT_EVENT" },
  { k: "drift_score", v: "0.84" },
  { k: "severity", v: "high" },
  { k: "routing_hint", v: "layer2_structural" },
  { k: "loop_a_trace", v: "trc_8f21" },
  { k: "citations", v: "[3]" },
  { k: "relationship_hints", v: "[2]" },
  { k: "entity_roles", v: "[4]" },
];

export const layer2Meta: DocNode = {
  id: "layer-2",
  layer: 2,
  title: "Layer 2 — Deep Multi-Modal Telemetry & Sovereign Reasoning Engine",
  short:
    "Event-driven orchestration triggered only after Layer 1 emits a DRIFT_EVENT. Fuses public drift with internal banking telemetry.",
  role: "Deep analytical and sovereign reasoning layer.",
  consumes: "Layer 1 DRIFT_EVENT payloads + Internal Banking Data.",
  produces: "Legal-ready compliance audit log with risk token, citations, and budget tracking.",
  why: "Heavy reasoning is only used when drift becomes structurally meaningful and materially confirmed by internal flows.",
};

export const layer2Nodes: DocNode[] = [
  {
    id: "graph-inversion",
    layer: 2,
    title: "Graph Topology Inversion",
    short: "Maps entity roles and relationship hints into Neo4j graph mutations.",
    role: "Translates DRIFT_EVENT context into graph operations.",
    consumes: "DRIFT_EVENT payload + existing Neo4j graph.",
    produces: "Graph mutations + structural deltas.",
    why: "Structural change in the entity graph is a leading indicator of compliance risk.",
  },
  {
    id: "volumetric-anomaly",
    layer: 2,
    title: "Volumetric Anomaly Detection",
    short: "TimeGPT verifies transaction velocity against Internal Banking Data.",
    role: "Time-series anomaly detector fed directly by internal banking feeds.",
    consumes: "Internal Banking Data (velocity, volume, dormancy) + DRIFT_EVENT context.",
    produces: "Anomaly trajectories and confidence intervals.",
    why: "Confirms whether public-signal drift is matched by behavioural change in real flows.",
  },
  {
    id: "imputation-matrix",
    layer: 2,
    title: "Multi-Modal Imputation Matrix",
    short: "Combines graph and time-series features into a unified feature matrix.",
    role: "Feature fusion layer.",
    consumes: "Graph deltas + volumetric anomalies.",
    produces: "Unified feature matrix for the survival model.",
    why: "Single-modality signals are noisy — fused features are what the survival model needs.",
  },
  {
    id: "survival-model",
    layer: 2,
    title: "Neural Deep Survival Model",
    short: "Computes the survival horizon T before compliance baseline decay.",
    role: "Predicts time-to-breach.",
    consumes: "Unified feature matrix.",
    produces: "Survival horizon T (days).",
    why: "T turns a fuzzy drift signal into an actionable deadline.",
  },
  {
    id: "t-decision",
    layer: 2,
    title: "T Decision Gate",
    short: "If T ≥ 7 days, keep low-cost tracking. If T < 7 days, escalate.",
    role: "Routing decision based on survival horizon.",
    consumes: "Survival horizon T.",
    produces: "Routing verdict: low-cost tracking or critical escalation.",
    why: "Concentrates expensive sovereign reasoning on truly urgent cases.",
  },
  {
    id: "sovereign-router",
    layer: 2,
    title: "Sovereign Guardrailed Router",
    short: "Routes critical cases to Swiss sovereign reasoning infrastructure.",
    role: "Guardrailed dispatcher with audit logging.",
    consumes: "Critical escalations from the T Decision Gate.",
    produces: "Reasoning request to Apertus / CSCS Alps.",
    why: "Sovereign routing is a hard regulatory requirement for sensitive Swiss compliance workloads.",
  },
  {
    id: "apertus",
    layer: 2,
    title: "Apertus / CSCS Alps Reasoning",
    short: "Generates audit-safe reasoning on Swiss sovereign AI infrastructure.",
    role: "Final reasoning engine — produces the legal-ready compliance verdict.",
    consumes: "Guardrailed reasoning request + full evidence bundle.",
    produces: "Risk token, summary, citations, recommended action.",
    why: "Audit-grade reasoning, fully on sovereign infrastructure, with traceable citations.",
  },
];

export const outputNode: DocNode = {
  id: "audit-output",
  layer: "output",
  title: "Legal-Ready Compliance Audit Log",
  short:
    "Audit-ready compliance output: risk token, FINMA-anchored summary, ZEFIX registry check, citations, budget, recommended action.",
  role: "Terminal artefact handed to compliance analysts and regulators.",
  consumes: "Apertus reasoning output + full pipeline telemetry.",
  produces: "Persisted, citable, regulator-presentable compliance decision.",
  why: "Every escalation ends in a single legal-ready artefact anchored against FINMA expectations and ZEFIX registry truth.",
};

export const outputChips = [
  "Risk Rating Token",
  "FINMA Anchored Summary",
  "ZEFIX Registry Check",
  "Source Citations",
  "Pipeline Budget",
  "Recommended Action",
];

export const metricChips = [
  "55%+ noise dropped locally",
  "$0.00 cloud fees during nominal screening",
  "0 LLM tokens",
  "0 heavy reasoner calls",
];

export const resilienceChips = [
  "ONNX fallback",
  "TF-IDF / hash fallback",
  "replay mode",
  "URL/title dedupe",
  "Pydantic recovery",
  "local audit trail",
  "no crash on network/auth failure",
];

export const advantageCards: { title: string; body: string }[] = [
  {
    title: "Cost Control",
    body: "Local filtering avoids unnecessary model calls.",
  },
  {
    title: "Predictive Horizon",
    body: "Survival model estimates Days-to-Breach T.",
  },
  {
    title: "Graph Precision",
    body: "Neo4j mutations reduce hallucinated relationships.",
  },
  {
    title: "Swiss Sovereignty",
    body: "Critical reasoning runs on Apertus / CSCS Alps.",
  },
];

export const allNodes: DocNode[] = [
  publicInputNode,
  internalInputNode,
  layer1Meta,
  ...layer1Nodes,
  bridgeNode,
  layer2Meta,
  ...layer2Nodes,
  outputNode,
];

// Play sequence order — public signals through L1, drift event, internal banking
// joins at volumetric anomaly, then through L2 to the legal-ready audit log.
export const playSequence: string[] = [
  "public-intelligence",
  ...layer1Nodes.map((n) => n.id),
  "drift-event",
  "graph-inversion",
  "internal-banking",
  "volumetric-anomaly",
  "imputation-matrix",
  "survival-model",
  "t-decision",
  "sovereign-router",
  "apertus",
  "audit-output",
];
