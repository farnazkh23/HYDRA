import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Activity, ShieldAlert, Users, TrendingUp } from "lucide-react";
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

function Dashboard() {
  const [nodes, setNodes] = useState<GraphNode[]>([]);
  const [edges, setEdges] = useState<GraphEdge[]>([]);
  const [customers, setCustomers] = useState<Customer[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [selected, setSelected] = useState<GraphNode | null>(null);

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
    return edges
      .filter((e) => e.source === selected.id || e.target === selected.id)
      .map((e) => (e.source === selected.id ? e.target : e.source));
  }, [selected, edges]);

  const lastAlert = useMemo(
    () => (selected ? alerts.find((a) => a.customerId === selected.id) : null),
    [selected, alerts],
  );

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
          <div className="flex gap-2">
            <Kpi icon={Users} label="Customers" value={String(stats.total)} />
            <Kpi icon={ShieldAlert} label="High Risk" value={String(stats.high)} tone="high" />
            <Kpi icon={Activity} label="Elevated" value={String(stats.elev)} tone="elevated" />
            <Kpi icon={TrendingUp} label="Avg Drift" value={`${stats.driftAvg}%`} />
          </div>
        </header>

        <div className="grid grid-cols-1 xl:grid-cols-[1fr_340px] gap-5">
          <NetworkGraph nodes={nodes} edges={edges} onSelect={setSelected} selectedId={selected?.id} />

          <aside className="rounded-2xl border border-border bg-card glass p-5 lime-outline">
            <div className="text-xs uppercase tracking-[0.18em] text-muted-foreground mb-3">
              Selected node
            </div>
            {selected ? (
              <>
                <div className="flex items-center justify-between gap-2">
                  <h3 className="font-display text-xl font-semibold">{selected.label}</h3>
                  <RiskBadge level={selected.riskStatus} />
                </div>
                <div className="mt-1 text-xs text-muted-foreground capitalize">{selected.type}</div>

                <dl className="mt-5 space-y-3 text-sm">
                  <Row k="Drift score" v={`${selected.driftScore}%`} />
                  <Row k="Last update" v={selected.lastUpdated} />
                  <Row k="Connected entities" v={String(connected.length)} />
                </dl>

                <div className="mt-5">
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-2">
                    Connections
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {connected.map((c) => (
                      <span key={c} className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-[11px]">
                        {nodes.find((n) => n.id === c)?.label ?? c}
                      </span>
                    ))}
                    {connected.length === 0 && (
                      <span className="text-xs text-muted-foreground">No links yet</span>
                    )}
                  </div>
                </div>

                <div className="mt-5 rounded-lg border border-border bg-surface-2/60 p-3">
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">
                    Latest alert
                  </div>
                  {lastAlert ? (
                    <>
                      <div className="text-sm font-medium">{lastAlert.title}</div>
                      <div className="text-xs text-muted-foreground mt-0.5">
                        {lastAlert.driftType} · {lastAlert.timestamp}
                      </div>
                    </>
                  ) : (
                    <div className="text-xs text-muted-foreground">No recent alerts.</div>
                  )}
                </div>
              </>
            ) : (
              <div className="text-sm text-muted-foreground">
                Drag any node to inspect. Click to select.
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
