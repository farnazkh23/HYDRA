import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Users, ShieldAlert, Activity, TrendingUp, TrendingDown, Minus, Zap, BarChart3 } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { RiskBadge } from "@/components/ui/risk-badge";
import { getPortfolio } from "@/lib/services";
import type { Customer, RiskStatus } from "@/lib/types";

export const Route = createFileRoute("/portfolio")({
  head: () => ({ meta: [{ title: "Portfolio — HYDRA" }] }),
  component: PortfolioPage,
});

type PortfolioData = {
  total_customers: number;
  risk_distribution: Record<string, number>;
  avg_drift_score: number;
  open_alerts: number;
  total_alerts: number;
  layer1_signals_processed: number;
  layer1_drop_rate: number;
  layer1_cost_usd: number;
  cost_per_1000_analyses_usd: number;
  customers: Customer[];
};

const riskOrder: RiskStatus[] = ["high", "elevated", "medium", "low"];

function TrendIcon({ trend }: { trend: "up" | "down" | "flat" }) {
  if (trend === "up") return <TrendingUp size={12} className="text-[color:var(--risk-high)]" />;
  if (trend === "down") return <TrendingDown size={12} className="text-[color:var(--risk-low)]" />;
  return <Minus size={12} className="text-muted-foreground" />;
}

function CustomerCard({ c }: { c: Customer }) {
  const barColor =
    c.riskStatus === "high"
      ? "bg-[color:var(--risk-high)]"
      : c.riskStatus === "elevated"
        ? "bg-[color:var(--risk-elevated)]"
        : c.riskStatus === "medium"
          ? "bg-[color:var(--risk-medium)]"
          : "bg-[color:var(--risk-low)]";

  return (
    <Link
      to="/customers/$id"
      params={{ id: c.id }}
      className="rounded-2xl border border-border bg-card glass p-5 flex flex-col gap-3 hover:border-neon/40 transition-colors lime-outline"
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <div className="font-display font-semibold truncate">{c.companyName}</div>
          <div className="text-[11px] text-muted-foreground truncate mt-0.5">{c.industry}</div>
        </div>
        <RiskBadge level={c.riskStatus} />
      </div>

      <div>
        <div className="flex justify-between text-[11px] text-muted-foreground mb-1">
          <span>Drift</span>
          <span className="flex items-center gap-1">
            <TrendIcon trend={c.trend} />
            {c.driftPercent}%
          </span>
        </div>
        <div className="h-1.5 w-full rounded-full bg-surface-2">
          <div
            className={`h-full rounded-full ${barColor} transition-all`}
            style={{ width: `${c.driftPercent}%` }}
          />
        </div>
      </div>

      <div className="flex items-center justify-between text-[11px] text-muted-foreground">
        <span>{c.kycStatus}</span>
        <span>{c.lastUpdated}</span>
      </div>
    </Link>
  );
}

function Kpi({
  icon: Icon,
  label,
  value,
  sub,
  tone,
}: {
  icon: React.ComponentType<{ size?: number; className?: string }>;
  label: string;
  value: string;
  sub?: string;
  tone?: "high" | "elevated" | "neon";
}) {
  const color =
    tone === "high"
      ? "text-[color:var(--risk-high)]"
      : tone === "elevated"
        ? "text-[color:var(--risk-elevated)]"
        : "text-neon";
  return (
    <div className="rounded-xl border border-border bg-card glass px-5 py-4 lime-outline">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <Icon size={12} />
        {label}
      </div>
      <div className={`mt-1.5 text-3xl font-display font-semibold ${color}`}>{value}</div>
      {sub && <div className="text-[11px] text-muted-foreground mt-0.5">{sub}</div>}
    </div>
  );
}

function PortfolioPage() {
  const [data, setData] = useState<PortfolioData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortfolio()
      .then((d) => setData(d as PortfolioData))
      .finally(() => setLoading(false));
  }, []);

  const sorted = data
    ? [...data.customers].sort(
        (a, b) => riskOrder.indexOf(a.riskStatus) - riskOrder.indexOf(b.riskStatus),
      )
    : [];

  const droppedPct = data ? Math.round(data.layer1_drop_rate * 100) : 0;
  const escalatedPct = 100 - droppedPct;

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1600px]">
        <header className="mb-8">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            Risk Intelligence
          </div>
          <h1 className="text-3xl font-display font-semibold">Portfolio Overview</h1>
          <p className="text-sm text-muted-foreground mt-1">
            All monitored clients ranked by risk exposure. HYDRA Loop A processes signals and drops stable ones cheaply — only genuine regime shifts escalate.
          </p>
        </header>

        {loading ? (
          <div className="text-sm text-muted-foreground animate-pulse">Loading portfolio…</div>
        ) : data ? (
          <>
            {/* KPI row */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
              <Kpi icon={Users} label="Clients" value={String(data.total_customers)} />
              <Kpi
                icon={ShieldAlert}
                label="High risk"
                value={String(data.risk_distribution.high ?? 0)}
                tone="high"
              />
              <Kpi
                icon={Activity}
                label="Elevated"
                value={String(data.risk_distribution.elevated ?? 0)}
                tone="elevated"
              />
              <Kpi
                icon={TrendingUp}
                label="Avg drift"
                value={`${data.avg_drift_score}%`}
                sub={`${data.open_alerts} open alert${data.open_alerts !== 1 ? "s" : ""}`}
              />
            </div>

            {/* Pipeline efficiency */}
            <div className="rounded-2xl border border-border bg-card glass p-5 mb-8 lime-outline">
              <div className="flex items-center justify-between mb-4">
                <div>
                  <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                    Loop A efficiency
                  </div>
                  <div className="font-display font-semibold flex items-center gap-2">
                    <Zap size={16} className="text-neon" />
                    {droppedPct}% of signals dropped cheaply — only {escalatedPct}% escalate to Layer 2
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-[11px] text-muted-foreground">Signals processed</div>
                  <div className="text-xl font-display font-semibold text-neon">
                    {data.layer1_signals_processed}
                  </div>
                </div>
              </div>
              <div className="h-2.5 w-full rounded-full bg-surface-2 overflow-hidden">
                <div
                  className="h-full rounded-full bg-neon/60 transition-all"
                  style={{ width: `${droppedPct}%` }}
                />
              </div>
              <div className="flex justify-between text-[11px] text-muted-foreground mt-2">
                <span className="text-neon/70">{droppedPct}% dropped (no LLM cost)</span>
                <span className="text-[color:var(--risk-elevated)]">{escalatedPct}% escalated to Layer 2</span>
              </div>
            </div>

            {/* Cost strip */}
            <div className="rounded-xl border border-border bg-card glass px-5 py-3 mb-8 flex items-center justify-between flex-wrap gap-3">
              <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
                <BarChart3 size={12} />
                Layer 1 cost
              </div>
              <div className="flex gap-6 text-sm">
                <span>
                  <span className="text-muted-foreground text-xs">This run: </span>
                  <span className="font-semibold text-neon">${data.layer1_cost_usd.toFixed(4)}</span>
                </span>
                <span>
                  <span className="text-muted-foreground text-xs">Per 1 000 analyses: </span>
                  <span className="font-semibold text-neon">${data.cost_per_1000_analyses_usd.toFixed(4)}</span>
                </span>
                <span>
                  <span className="text-muted-foreground text-xs">LLM tokens used: </span>
                  <span className="font-semibold text-neon">0</span>
                </span>
              </div>
            </div>

            {/* Customer grid */}
            <div className="mb-4">
              <div className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
                All clients
              </div>
              <h2 className="text-lg font-display font-semibold">Risk heatmap</h2>
            </div>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {sorted.map((c) => (
                <CustomerCard key={c.id} c={c} />
              ))}
            </div>
          </>
        ) : (
          <div className="text-sm text-muted-foreground">Failed to load portfolio data.</div>
        )}
      </div>
    </AppLayout>
  );
}
