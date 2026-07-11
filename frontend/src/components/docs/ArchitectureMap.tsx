import { ArrowDown } from "lucide-react";
import { ComponentCard } from "./ComponentCard";
import {
  bridgeFields,
  bridgeNode,
  internalInputNode,
  publicInputNode,
  layer1Meta,
  layer1Nodes,
  layer2Meta,
  layer2Nodes,
  metricChips,
  outputChips,
  outputNode,
  resilienceChips,
  type DocNode,
} from "@/lib/documentation-data";

export function ArchitectureMap({
  selectedId,
  visitedIds,
  currentActiveId,
  onSelect,
}: {
  selectedId: string | null;
  visitedIds: string[];
  currentActiveId: string | null;
  onSelect: (id: string) => void;
}) {
  const isVisited = (id: string) => visitedIds.includes(id);
  const isActive = (id: string) => currentActiveId === id;
  const driftReached = isVisited("drift-event") || isActive("drift-event");
  const internalReached =
    isVisited(internalInputNode.id) || isActive(internalInputNode.id);

  return (
    <div className="space-y-4">
      {/* Dual input pills */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <InputPill
          node={publicInputNode}
          flowLabel="→ flows into Layer 1"
          selected={selectedId === publicInputNode.id}
          visited={isVisited(publicInputNode.id)}
          active={isActive(publicInputNode.id)}
          onClick={onSelect}
        />
        <InputPill
          node={internalInputNode}
          flowLabel="→ flows into Layer 2 · Volumetric Anomaly"
          selected={selectedId === internalInputNode.id}
          visited={isVisited(internalInputNode.id)}
          active={isActive(internalInputNode.id)}
          onClick={onSelect}
        />
      </div>

      {/* Split arrows */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
        <Arrow />
        <Arrow muted />
      </div>

      {/* Layer 1 */}
      <LayerContainer
        meta={layer1Meta}
        selected={selectedId === layer1Meta.id}
        active={isActive(layer1Meta.id)}
        onSelect={onSelect}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2.5">
          {layer1Nodes.map((n) => (
            <ComponentCard
              key={n.id}
              node={n}
              selected={selectedId === n.id}
              visited={isVisited(n.id)}
              active={isActive(n.id)}
              onClick={onSelect}
            />
          ))}
        </div>

        {/* Branching paths */}
        <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
          <div className="rounded-lg border bg-surface/60 px-3 py-2 text-[11px] text-muted-foreground flex items-center gap-2 transition-all border-border">
            <span className="h-1.5 w-6 rounded-full bg-muted-foreground/40" />
            Stable signal → dropped cheaply → nominal VAE snapshot
          </div>
          <div
            className={`rounded-lg border px-3 py-2 text-[11px] flex items-center gap-2 transition-all ${
              driftReached
                ? "border-neon/40 bg-neon-soft text-neon"
                : "border-border bg-surface/60 text-muted-foreground"
            }`}
          >
            <span
              className={`h-1.5 w-6 rounded-full transition-all ${
                driftReached
                  ? "bg-neon shadow-[0_0_10px_var(--neon)]"
                  : "bg-muted-foreground/40"
              }`}
            />
            Suspicious signal → reconstruction error → DRIFT_EVENT emitted
          </div>
        </div>

        {/* Metric chips */}
        <div className="mt-3 flex flex-wrap gap-1.5">
          {metricChips.map((m) => (
            <span
              key={m}
              className="rounded-md border border-neon/30 bg-surface/60 px-2 py-0.5 text-[10px] font-mono text-muted-foreground"
            >
              {m}
            </span>
          ))}
        </div>
      </LayerContainer>

      <Arrow />

      {/* DRIFT_EVENT bridge */}
      <button
        type="button"
        onClick={() => onSelect(bridgeNode.id)}
        className={`mx-auto block w-full max-w-3xl rounded-2xl bg-card/70 backdrop-blur px-5 py-4 text-left transition-all hover-lift border ${
          isVisited(bridgeNode.id) ? "border-neon/40" : "border-border"
        } ${
          isActive(bridgeNode.id)
            ? "ring-2 ring-neon shadow-[0_0_36px_oklch(0.92_0.22_128/0.45)]"
            : ""
        } ${selectedId === bridgeNode.id ? "lime-outline" : ""}`}
      >
        <div className="flex flex-col gap-3">
          <div>
            <div className="font-display text-[10px] uppercase tracking-[0.22em] text-neon">
              Bridge Payload
            </div>
            <div className="font-display text-base mt-0.5">DRIFT_EVENT PAYLOAD</div>
            <div className="text-[11px] text-muted-foreground mt-0.5">
              Layer 2 only wakes when this typed payload is emitted.
            </div>
          </div>
          <div className="flex flex-wrap gap-1.5">
            {bridgeFields.map((f) => (
              <span
                key={f.k}
                className="rounded-md border border-neon/30 bg-surface-2 px-2 py-0.5 text-[10px] font-mono"
              >
                <span className="text-muted-foreground">{f.k}:</span>{" "}
                <span className="text-neon">{f.v}</span>
              </span>
            ))}
          </div>
        </div>
      </button>

      <Arrow />

      {/* Layer 2 */}
      <LayerContainer
        meta={layer2Meta}
        selected={selectedId === layer2Meta.id}
        active={isActive(layer2Meta.id)}
        onSelect={onSelect}
      >
        {/* Internal banking inflow indicator */}
        <div
          className={`mb-3 rounded-lg border px-3 py-2 text-[11px] flex items-center gap-2 transition-all ${
            internalReached
              ? "border-neon/40 bg-neon-soft text-neon"
              : "border-border bg-surface/60 text-muted-foreground"
          }`}
        >
          <span
            className={`h-1.5 w-6 rounded-full transition-all ${
              internalReached
                ? "bg-neon shadow-[0_0_10px_var(--neon)]"
                : "bg-muted-foreground/40"
            }`}
          />
          Internal Banking Data → Volumetric Anomaly Detection (TimeGPT)
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-2.5">
          {layer2Nodes.slice(0, 4).map((n) => (
            <ComponentCard
              key={n.id}
              node={n}
              selected={selectedId === n.id}
              visited={isVisited(n.id)}
              active={isActive(n.id)}
              onClick={onSelect}
            />
          ))}
        </div>

        {/* T-decision diamond */}
        <div className="mt-4 flex flex-col items-center gap-3">
          <div className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            T Decision Gate
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3 w-full">
            <div className={`rounded-lg border px-3 py-2 text-[11px] transition-all ${
              isVisited("t-decision") || isActive("t-decision")
                ? "border-border bg-surface/60 text-muted-foreground"
                : "border-border bg-surface/60 text-muted-foreground"
            }`}>
              <div className="font-mono text-foreground/80">T ≥ 7 days</div>
              <div>→ Low-cost tracking pass</div>
            </div>
            <div className={`rounded-lg border px-3 py-2 text-[11px] transition-all ${
              isVisited("t-decision") || isActive("t-decision")
                ? "border-2 border-[color:var(--risk-high)] bg-[color:var(--risk-high)]/15 text-[color:var(--risk-high)] shadow-[0_0_24px_oklch(0.65_0.24_25/0.35)]"
                : "border-border bg-surface/60 text-muted-foreground"
            }`}>
              <div className={`font-mono ${isVisited("t-decision") || isActive("t-decision") ? "font-semibold" : "text-foreground/80"}`}>T &lt; 7 days</div>
              <div>→ Critical Drift Breach</div>
              <div>→ Sovereign Swiss Reasoning</div>
              <div>→ Apertus / CSCS Alps</div>
            </div>
          </div>
        </div>

        <div className="mt-3 grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-3 gap-2.5">
          {layer2Nodes.slice(4).map((n) => (
            <ComponentCard
              key={n.id}
              node={n}
              selected={selectedId === n.id}
              visited={isVisited(n.id)}
              active={isActive(n.id)}
              critical={n.id === "apertus" || n.id === "sovereign-router"}
              onClick={onSelect}
            />
          ))}
        </div>
      </LayerContainer>

      {/* Resilience & Guardrails strip */}
      <div className="rounded-xl border border-border/70 bg-surface/40 px-4 py-3">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2">
          <div className="font-display text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
            Resilience & Guardrails
          </div>
          <div className="flex flex-wrap gap-1.5">
            {resilienceChips.map((c) => (
              <span
                key={c}
                className="rounded-md border border-border bg-surface-2/70 px-2 py-0.5 text-[10px] font-mono text-muted-foreground"
              >
                {c}
              </span>
            ))}
          </div>
        </div>
      </div>

      <Arrow />

      {/* Output */}
      <button
        type="button"
        onClick={() => onSelect(outputNode.id)}
        className={`block w-full rounded-2xl border bg-card/70 backdrop-blur px-5 py-4 text-left transition-all hover-lift ${
          isVisited(outputNode.id) ? "border-neon/40" : "border-neon/30"
        } ${
          isActive(outputNode.id)
            ? "ring-2 ring-neon shadow-[0_0_28px_oklch(0.92_0.22_128/0.4)]"
            : ""
        } ${selectedId === outputNode.id ? "lime-outline" : ""}`}
      >
        <div className="font-display text-[10px] uppercase tracking-[0.22em] text-neon">
          Output
        </div>
        <div className="font-display text-base mt-0.5">LEGAL-READY COMPLIANCE AUDIT LOG</div>
        <div className="text-[11px] text-muted-foreground mt-0.5">
          Audit-ready compliance output — FINMA anchored, ZEFIX verified, fully cited.
        </div>
        <div className="mt-3 flex flex-wrap gap-1.5">
          {outputChips.map((c) => (
            <span
              key={c}
              className="rounded-md border border-neon/30 bg-surface-2 px-2 py-0.5 text-[10px] font-mono text-foreground/85"
            >
              {c}
            </span>
          ))}
        </div>
      </button>
    </div>
  );
}

function Arrow({ muted = false }: { muted?: boolean }) {
  return (
    <div className="flex justify-center">
      <ArrowDown size={18} className={muted ? "text-muted-foreground/50" : "text-neon/60"} />
    </div>
  );
}

function InputPill({
  node,
  flowLabel,
  selected,
  visited,
  active,
  onClick,
}: {
  node: DocNode;
  flowLabel: string;
  selected?: boolean;
  visited?: boolean;
  active?: boolean;
  onClick: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(node.id)}
      className={`block w-full rounded-2xl border bg-surface-2/80 px-4 py-3 text-left transition-all hover-lift ${
        selected ? "lime-outline" : visited ? "border-neon/40" : "border-border"
      } ${active ? "ring-2 ring-neon/60 shadow-[0_0_18px_oklch(0.92_0.22_128/0.3)]" : ""}`}
    >
      <div className="font-display text-[10px] uppercase tracking-[0.22em] text-neon">
        Input
      </div>
      <div className="font-display text-sm mt-0.5 uppercase tracking-wider">
        {node.title}
      </div>
      <div className="text-[11px] text-muted-foreground mt-1">{node.short}</div>
      <div className="text-[10px] font-mono text-neon/70 mt-2">{flowLabel}</div>
    </button>
  );
}

function LayerContainer({
  meta,
  selected,
  active,
  onSelect,
  children,
}: {
  meta: DocNode;
  selected: boolean;
  active: boolean;
  onSelect: (id: string) => void;
  children: React.ReactNode;
}) {
  return (
    <div
      className={`rounded-2xl border bg-card/60 backdrop-blur grid-bg p-4 sm:p-5 transition-all ${
        selected ? "lime-outline" : "border-neon/30"
      } ${active ? "ring-2 ring-neon/50 shadow-[0_0_36px_oklch(0.92_0.22_128/0.25)]" : ""}`}
    >
      <button
        type="button"
        onClick={() => onSelect(meta.id)}
        className="block text-left w-full mb-3"
      >
        <div className="font-display text-[10px] uppercase tracking-[0.22em] text-neon">
          {meta.layer === 1 ? "Layer 01" : "Layer 02"}
        </div>
        <h2 className="font-display text-base sm:text-lg uppercase tracking-wider mt-0.5">
          {meta.title.replace(/^Layer \d+ — /, "")}
        </h2>
        <p className="text-[12px] text-muted-foreground mt-1 max-w-3xl">{meta.short}</p>
      </button>
      {children}
    </div>
  );
}
