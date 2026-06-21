import { useEffect, useMemo, useRef, useState } from "react";
import type { GraphEdge, GraphNode, RiskStatus } from "@/lib/types";

const RISK_COLOR: Record<RiskStatus, string> = {
  low: "oklch(0.78 0.18 150)",
  medium: "oklch(0.86 0.17 95)",
  elevated: "oklch(0.75 0.18 50)",
  high: "oklch(0.65 0.24 25)",
};

interface SimNode extends GraphNode {
  x: number;
  y: number;
  vx: number;
  vy: number;
  fx?: number | null;
  fy?: number | null;
}

export function NetworkGraph({
  nodes,
  edges,
  onSelect,
  selectedId,
}: {
  nodes: GraphNode[];
  edges: GraphEdge[];
  onSelect?: (n: GraphNode | null) => void;
  selectedId?: string | null;
}) {
  const wrapRef = useRef<HTMLDivElement>(null);
  const [size, setSize] = useState({ w: 800, h: 560 });
  const [, force] = useState(0);
  const drag = useRef<{ id: string; offX: number; offY: number } | null>(null);

  const simNodes = useRef<SimNode[]>([]);
  // Sync simNodes when the nodes prop changes (e.g. after async fetch resolves).
  // Preserve positions of nodes that already exist so the layout doesn't reset.
  useEffect(() => {
    if (nodes.length === 0) return;
    const existing = new Map(simNodes.current.map((n) => [n.id, n]));
    simNodes.current = nodes.map((n, i) => {
      const prev = existing.get(n.id);
      if (prev) return { ...prev, ...n };
      const a = (i / nodes.length) * Math.PI * 2;
      return { ...n, x: 400 + Math.cos(a) * 200, y: 280 + Math.sin(a) * 180, vx: 0, vy: 0 };
    });
  }, [nodes]);

  useEffect(() => {
    const el = wrapRef.current;
    if (!el) return;
    const ro = new ResizeObserver(() => {
      setSize({ w: el.clientWidth, h: el.clientHeight });
    });
    ro.observe(el);
    return () => ro.disconnect();
  }, []);

  // Simple force simulation
  useEffect(() => {
    let raf = 0;
    const tick = () => {
      const ns = simNodes.current;
      const W = size.w, H = size.h;
      const cx = W / 2, cy = H / 2;
      // repulsion
      for (let i = 0; i < ns.length; i++) {
        for (let j = i + 1; j < ns.length; j++) {
          const a = ns[i], b = ns[j];
          const dx = b.x - a.x, dy = b.y - a.y;
          const d2 = dx * dx + dy * dy + 0.01;
          const d = Math.sqrt(d2);
          const f = 4200 / d2;
          const fx = (dx / d) * f, fy = (dy / d) * f;
          a.vx -= fx; a.vy -= fy;
          b.vx += fx; b.vy += fy;
        }
      }
      // attraction along edges
      for (const e of edges) {
        const a = ns.find((n) => n.id === e.source);
        const b = ns.find((n) => n.id === e.target);
        if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const d = Math.sqrt(dx * dx + dy * dy) || 1;
        const f = (d - 160) * 0.012;
        a.vx += (dx / d) * f; a.vy += (dy / d) * f;
        b.vx -= (dx / d) * f; b.vy -= (dy / d) * f;
      }
      // gravity to center + damping + integrate
      for (const n of ns) {
        if (n.fx != null && n.fy != null) {
          n.x = n.fx; n.y = n.fy; n.vx = 0; n.vy = 0;
          continue;
        }
        n.vx += (cx - n.x) * 0.002;
        n.vy += (cy - n.y) * 0.002;
        n.vx *= 0.82; n.vy *= 0.82;
        n.x += n.vx; n.y += n.vy;
        n.x = Math.max(40, Math.min(W - 40, n.x));
        n.y = Math.max(40, Math.min(H - 40, n.y));
      }
      force((v) => (v + 1) % 1000000);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [edges, size]);

  const nodeById = useMemo(() => {
    const m = new Map<string, SimNode>();
    simNodes.current.forEach((n) => m.set(n.id, n));
    return m;
  }, [simNodes.current.length]);

  const handleDown = (e: React.PointerEvent, n: SimNode) => {
    (e.target as Element).setPointerCapture(e.pointerId);
    drag.current = { id: n.id, offX: e.clientX - n.x, offY: e.clientY - n.y };
    n.fx = n.x; n.fy = n.y;
    onSelect?.(n);
  };
  const handleMove = (e: React.PointerEvent) => {
    if (!drag.current) return;
    const rect = wrapRef.current!.getBoundingClientRect();
    const n = simNodes.current.find((x) => x.id === drag.current!.id);
    if (!n) return;
    n.fx = e.clientX - rect.left;
    n.fy = e.clientY - rect.top;
  };
  const handleUp = () => {
    if (!drag.current) return;
    const n = simNodes.current.find((x) => x.id === drag.current!.id);
    if (n) { n.fx = null; n.fy = null; }
    drag.current = null;
  };

  return (
    <div
      ref={wrapRef}
      className="relative h-[560px] w-full overflow-hidden rounded-2xl border border-border bg-[oklch(0.13_0.005_240)] grid-bg"
      onPointerMove={handleMove}
      onPointerUp={handleUp}
      onPointerLeave={handleUp}
    >
      <div className="absolute top-3 left-3 z-10 flex items-center gap-2">
        <span className="rounded-md border border-neon/30 bg-neon-soft px-2 py-1 text-[11px] font-medium text-neon">
          ● Live GraphRAG placeholder
        </span>
      </div>
      <Legend />
      <svg className="absolute inset-0 h-full w-full">
        <defs>
          <marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" orient="auto">
            <path d="M0,0 L10,5 L0,10 Z" fill="oklch(1 0 0 / 0.25)" />
          </marker>
          <filter id="nodeGlow" x="-100%" y="-100%" width="300%" height="300%">
            <feGaussianBlur stdDeviation="4" />
          </filter>
        </defs>
        {edges.map((e, i) => {
          const a = nodeById.get(e.source);
          const b = nodeById.get(e.target);
          if (!a || !b) return null;
          const isNew = e.isNewlyDetected;
          return (
            <g key={i}>
              <line
                x1={a.x} y1={a.y} x2={b.x} y2={b.y}
                stroke={isNew ? RISK_COLOR.high : "oklch(1 0 0 / 0.12)"}
                strokeWidth={isNew ? 2 : 1}
                strokeDasharray={isNew ? "6 4" : undefined}
                markerEnd="url(#arr)"
              >
                {isNew && (
                  <animate attributeName="stroke-dashoffset" from="0" to="20" dur="1.2s" repeatCount="indefinite" />
                )}
              </line>
              {isNew && (
                <text
                  x={(a.x + b.x) / 2}
                  y={(a.y + b.y) / 2 - 6}
                  textAnchor="middle"
                  fontSize="10"
                  fill={RISK_COLOR.high}
                  className="font-mono"
                >
                  New beneficial-owner link detected
                </text>
              )}
            </g>
          );
        })}
        {simNodes.current.map((n) => {
          const c = RISK_COLOR[n.riskStatus];
          const sel = selectedId === n.id;
          const r = n.type === "company" ? 16 : n.type === "jurisdiction" ? 12 : 14;
          return (
            <g
              key={n.id}
              onPointerDown={(e) => handleDown(e, n)}
              style={{ cursor: "grab" }}
            >
              <circle cx={n.x} cy={n.y} r={r + 8} fill={c} opacity={0.18} filter="url(#nodeGlow)" />
              <circle
                cx={n.x} cy={n.y} r={r}
                fill="oklch(0.18 0.005 240)"
                stroke={c}
                strokeWidth={sel ? 3 : 1.5}
              />
              <circle cx={n.x} cy={n.y} r={r - 5} fill={c} opacity={0.6} />
              <text
                x={n.x} y={n.y + r + 14}
                textAnchor="middle"
                fontSize="11"
                fill="oklch(0.95 0.005 240)"
                className="font-display select-none pointer-events-none"
              >
                {n.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}

function Legend() {
  const items: { label: string; level: RiskStatus }[] = [
    { label: "Low", level: "low" },
    { label: "Medium", level: "medium" },
    { label: "Elevated", level: "elevated" },
    { label: "High / Critical", level: "high" },
  ];
  return (
    <div className="absolute bottom-3 left-3 z-10 flex items-center gap-3 rounded-lg border border-border bg-card/80 px-3 py-2 text-[11px] backdrop-blur">
      <span className="text-muted-foreground">Risk:</span>
      {items.map((i) => (
        <span key={i.level} className="inline-flex items-center gap-1.5">
          <span className="h-2.5 w-2.5 rounded-full" style={{ background: RISK_COLOR[i.level] }} />
          {i.label}
        </span>
      ))}
    </div>
  );
}
