import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, ShieldAlert, Users, TrendingUp, Radio } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { NetworkGraph } from "@/components/NetworkGraph";
import { RiskBadge } from "@/components/ui/risk-badge";
import { getAlerts, getCustomers, getGraph } from "@/lib/services";
import type { Alert, Customer, GraphEdge, GraphNode } from "@/lib/types";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "HYDRA — Compliance Cockpit" },
      { name: "description", content: "Dark, premium bank compliance dashboard for AML/KYC drift intelligence." },
    ],
  }),
  component: Dashboard,
});

function useLiveFeed() {
  const [connected, setConnected] = useState(false);
  const [alertCount, setAlertCount] = useState(0);
  const [lastEvent, setLastEvent] = useState<string | null>(null);
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    const es = new EventSource("/api/events/stream");
    esRef.current = es;
    es.onopen = () => setConnected(true);
    es.onerror = () => setConnected(false);
    es.onmessage = (e) => {
      try {
        const msg = JSON.parse(e.data);
        if (msg.type === "heartbeat") setAlertCount(msg.alert_count ?? 0);
        if (msg.type === "new_alert") setLastEvent(msg.alert?.title ?? "New alert");
      } catch {}
    };
    return () => { es.close(); setConnected(false); };
  }, []);

  return { connected, alertCount, lastEvent };
}

function Dashboard() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);
  const live = useLiveFeed();

  useEffect(() => {
    getGraph().then((g) => {
      setNodes(g.nodes); setEdges(g.edges);
      setSelected(g.nodes.find((n) => n.id === "spacex") ?? null);
    });
    getCustomers().then(setCustomers);
    getAlerts().then(setAlerts);
  }, []);

  const stats = useMemo(() => {
    const high = customers.filter((c) => c.riskStatus === "high").length;
    const elev = customers.filter((c) => c.riskStatus === "elevated").length;
    const driftAvg = customers.length
      ? Math.round(customers.reduce((s, c) => s + c.driftPercent, 0) / customers.length)
      : 0;
    return { high, elev, driftAvg, total: customers.length };
  }, [customers]);

  const connected = useMemo(() => {
    if (!selected) return [];
    const ids = edges
      .filter((e) => e.source === selected.id || e.target === selected.id)
      .map((e) => (e.source === selected.id ? e.target : e.source));
    return [...new Set(ids)]; // deduplicate
  }, [selected, edges]);

  const lastAlert = useMemo(() => {
    if (!selected) return null;
    return alerts.find(
      (a) =>
        a.customerId === selected.id ||
        a.customerId.replace("demo-", "").replace(/-001$/, "") === selected.id ||
        a.customerId.includes(selected.id),
    );
  }, [selected, alerts]);

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1600px]">
        <header className="mb-6 flex items-end justify-between flex-wrap gap-4">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
              Network Intelligence
            </div>
            <h1 className="text-3xl font-display font-semibold">Dashboard</h1>
            <p className="text-sm text-muted-foreground mt-1 max-w-2xl">
              Most customer signals are stable and dropped cheaply. Only suspicious regime shifts are escalated —
              this is what HYDRA is watching right now.
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <Kpi icon={Users} label="Customers" value={String(stats.total)} />
            <Kpi icon={ShieldAlert} label="High Risk" value={String(stats.high)} tone="high" />
            <Kpi icon={Activity} label="Elevated" value={String(stats.elev)} tone="elevated" />
            <Kpi icon={TrendingUp} label="Avg Drift" value={`${stats.driftAvg}%`} />
            <div className="rounded-xl border border-border bg-card glass px-4 py-3 min-w-[120px] lime-outline flex flex-col justify-between">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
                <Radio size={12} /> Live
              </div>
              <div className="mt-1 flex items-center gap-1.5">
                <span className={`h-2 w-2 rounded-full ${live.connected ? "bg-neon animate-pulse" : "bg-muted-foreground"}`} />
                <span className="text-sm font-semibold text-neon">{live.connected ? "Connected" : "Connecting…"}</span>
              </div>
              {live.alertCount > 0 && (
                <div className="text-[10px] text-muted-foreground mt-0.5">{live.alertCount} alert{live.alertCount !== 1 ? "s" : ""} in DB</div>
              )}
            </div>
          </div>
        </header>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-5">
          <NetworkGraph nodes={nodes} edges={edges} onSelect={setSelected} selectedId={selected?.id} />

          <aside className="rounded-2xl border border-border bg-card glass p-5 lime-outline">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">
              Selected node
            </div>
            {selected ? (
              selected.type === "company" ? (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-display text-xl font-semibold">{selected.label}</h3>
                    <RiskBadge level={selected.riskStatus} />
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground">Company</div>
                  <dl className="mt-5 space-y-3 text-sm">
                    <Row k="Drift score" v={`${selected.driftScore}%`} />
                    <Row k="Last update" v={selected.lastUpdated} />
                    <Row k="Connected entities" v={String(connected.length)} />
                  </dl>
                  <div className="mt-5">
                    <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Connections</div>
                    <div className="flex flex-wrap gap-1.5">
                      {connected.map((c, i) => (
                        <span key={`${c}-${i}`} className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-[11px]">
                          {nodes.find((n) => n.id === c)?.label ?? c}
                        </span>
                      ))}
                      {connected.length === 0 && <span className="text-xs text-muted-foreground">No links yet</span>}
                    </div>
                  </div>
                  {lastAlert ? (
                    <Link to="/alerts/$id" params={{ id: lastAlert.id }}>
                      <div className="mt-5 rounded-lg border border-border bg-surface-2/60 p-3 cursor-pointer hover:border-neon/50 hover:bg-surface-2/80 transition-colors">
                        <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Latest alert</div>
                        <div className="text-sm font-medium">{lastAlert.title}</div>
                        <div className="text-xs text-muted-foreground mt-0.5">{lastAlert.driftType} · {lastAlert.timestamp}</div>
                      </div>
                    </Link>
                  ) : (
                    <div className="mt-5 rounded-lg border border-border bg-surface-2/60 p-3">
                      <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">Latest alert</div>
                      <div className="text-xs text-muted-foreground">No alerts in window.</div>
                    </div>
                  )}
                </>
              ) : (
                <>
                  <div className="flex items-center justify-between gap-2">
                    <h3 className="font-display text-lg font-semibold">{selected.label}</h3>
                  </div>
                  <div className="mt-1 text-xs text-muted-foreground capitalize">KG entity · {selected.type}</div>
                  <div className="mt-5">
                    <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">Linked to</div>
                    <div className="flex flex-wrap gap-1.5">
                      {connected.map((c) => {
                        const n = nodes.find((n) => n.id === c);
                        return n?.type === "company" ? (
                          <Link key={c} to="/customers/$id" params={{ id: c }}>
                            <span className="rounded-md border border-neon/40 bg-neon-soft px-2 py-0.5 text-[11px] text-neon cursor-pointer hover:bg-neon/20">
                              {n.label}
                            </span>
                          </Link>
                        ) : (
                          <span key={c} className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-[11px]">
                            {n?.label ?? c}
                          </span>
                        );
                      })}
                      {connected.length === 0 && <span className="text-xs text-muted-foreground">No links yet</span>}
                    </div>
                  </div>
                  <div className="mt-4 text-xs text-muted-foreground">
                    This entity was detected via GraphRAG from real news signals.
                  </div>
                </>
              )
            ) : (
              <div className="text-sm text-muted-foreground">
                Click any node to inspect.
              </div>
            )}
          </aside>
        </div>
      </div>
    </AppLayout>
  );
}

function Kpi({
  icon: Icon, label, value, tone,
}: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; value: string; tone?: "high" | "elevated" }) {
  const color =
    tone === "high" ? "text-[color:var(--risk-high)]" : tone === "elevated" ? "text-[color:var(--risk-elevated)]" : "text-neon";
  return (
    <div className="rounded-xl border border-border bg-card glass px-4 py-3 min-w-[120px] lime-outline">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <Icon size={12} /> {label}
      </div>
      <div className={`mt-1 text-2xl font-display font-semibold ${color}`}>{value}</div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <div className="flex items-center justify-between">
      <dt className="text-muted-foreground">{k}</dt>
      <dd className="text-foreground/90">{v}</dd>
    </div>
  );
}
