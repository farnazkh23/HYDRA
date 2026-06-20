import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { AppLayout } from "@/components/layout/AppLayout";
import { getLogs } from "@/lib/services";

export const Route = createFileRoute("/logs")({
  head: () => ({ meta: [{ title: "Logs — HYDRA" }] }),
  component: LogsPage,
});

const filters = ["All", "Loop A", "Loop B", "GraphRAG", "TimeGPT", "Router", "Guardrails", "Errors"] as const;

function LogsPage() {
  type Log = { ts: string; level: "info" | "warn" | "error"; module: string; msg: string };
  const [base, setBase] = useState<Log[]>([]);
  const [extra, setExtra] = useState<Log[]>([]);
  const [filter, setFilter] = useState<(typeof filters)[number]>("All");
  const boxRef = useRef<HTMLDivElement>(null);

  useEffect(() => { getLogs().then(setBase); }, []);

  // Append live-feeling lines
  useEffect(() => {
    const samples: Omit<Log, "ts">[] = [
      { level: "info", module: "Loop A", msg: "RawSignal received: NVIDIA / Filings" },
      { level: "info", module: "Loop A", msg: "reconstruction_error=0.18 below threshold — dropped cheaply" },
      { level: "warn", module: "TimeGPT", msg: "anomaly_score=0.73 horizon=14d" },
      { level: "info", module: "Router", msg: "path=cheap reason=score<0.8" },
      { level: "info", module: "Guardrails", msg: "all citations verified" },
      { level: "error", module: "GraphRAG", msg: "neo4j read replica lag 1.2s (recovered)" },
    ];
    let i = 0;
    const t = setInterval(() => {
      const now = new Date();
      const ts = now.toTimeString().slice(0, 8);
      setExtra((cur) => [...cur, { ts, ...samples[i % samples.length] }].slice(-200));
      i++;
    }, 1800);
    return () => clearInterval(t);
  }, []);

  const all = useMemo(() => [...base, ...extra], [base, extra]);
  const visible = useMemo(() => {
    if (filter === "All") return all;
    if (filter === "Errors") return all.filter((l) => l.level === "error");
    return all.filter((l) => l.module.toLowerCase() === filter.toLowerCase() || l.module === filter);
  }, [all, filter]);

  useEffect(() => {
    boxRef.current?.scrollTo({ top: boxRef.current.scrollHeight });
  }, [visible.length]);

  const msgColor = (l: "info" | "warn" | "error") =>
    l === "error"
      ? "text-[oklch(0.72_0.22_25)]"
      : l === "warn"
        ? "text-[oklch(0.82_0.18_70)]"
        : "text-[oklch(0.92_0.22_128)]";

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1400px]">
        <header className="mb-6">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">Engine telemetry</div>
          <h1 className="text-3xl font-display font-semibold">Logs</h1>
          <p className="text-sm text-muted-foreground mt-1">Real-time HYDRA engine output for technical specialists.</p>
        </header>

        <div className="flex flex-wrap gap-1.5 mb-3">
          {filters.map((f) => (
            <button
              key={f}
              onClick={() => setFilter(f)}
              className={`rounded-md px-3 py-1.5 text-xs ${
                filter === f ? "bg-neon-soft text-neon border border-neon/30" : "border border-border text-muted-foreground hover:text-foreground"
              }`}
            >
              {f}
            </button>
          ))}
        </div>

        <div
          ref={boxRef}
          className="rounded-2xl border border-[oklch(1_0_0/0.08)] bg-[oklch(0.13_0.005_240)] p-5 font-mono text-[13px] leading-[1.7] h-[560px] overflow-y-auto scrollbar-thin shadow-[inset_0_0_60px_oklch(0.92_0.22_128/0.05)] lime-outline"
        >
          {visible.map((l, i) => (
            <div key={i} className="flex items-baseline gap-3 py-0.5">
              <span className="text-[oklch(0.72_0.01_240)] tabular-nums shrink-0">[{l.ts}]</span>
              <span className="text-[oklch(1_0_0/0.18)] shrink-0">│</span>
              <span className="text-[oklch(0.78_0.05_200)] w-24 shrink-0 font-medium">{l.module}</span>
              <span className="text-[oklch(1_0_0/0.18)] shrink-0">│</span>
              <span className={`${msgColor(l.level)} break-words`}>{l.msg}</span>
            </div>
          ))}
          <div className="text-[oklch(0.92_0.22_128)] animate-pulse mt-1">▍</div>
        </div>
      </div>
    </AppLayout>
  );
}
