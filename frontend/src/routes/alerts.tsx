import { createFileRoute, Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { RiskBadge } from "@/components/ui/risk-badge";
import type { RiskStatus } from "@/lib/types";

export const Route = createFileRoute("/alerts")({
  head: () => ({ meta: [{ title: "Alerts — HYDRA" }] }),
  component: AlertsRouteShell,
});

const alerts = [
  {
    id: "alert_001",
    customerId: "spacex",
    customerName: "SpaceX",
    title: "New beneficial owner identified",
    severity: "high",
    severityLabel: "High Risk",
    driftType: "Ownership Drift",
    timestamp: "2 min ago",
    explanation:
      "GraphRAG detected an undisclosed UBO link via Offshore Holding Ltd. Triple added with HIGH confidence.",
  },
  {
    id: "alert_002",
    customerId: "offshore-holding",
    customerName: "Offshore Holding Ltd",
    title: "Sanctions screening hit",
    severity: "high",
    severityLabel: "High Risk",
    driftType: "Compliance Drift",
    timestamp: "6h ago",
    explanation: "PEP screening surfaced a politically exposed connected party.",
  },
  {
    id: "alert_003",
    customerId: "binance",
    customerName: "Binance Holdings",
    title: "Transaction pattern anomaly",
    severity: "elevated",
    severityLabel: "Elevated Risk",
    driftType: "Transaction Drift",
    timestamp: "14 min ago",
    explanation: "TimeGPT anomaly_score=0.91 — projected 3× volume spike within 5 days.",
  },
  {
    id: "alert_004",
    customerId: "amazon",
    customerName: "Amazon",
    title: "Adverse media signal",
    severity: "elevated",
    severityLabel: "Elevated Risk",
    driftType: "Behavioral Drift",
    timestamp: "3h ago",
    explanation: "Loop A reconstruction error 0.62 with negative-sentiment keywords.",
  },
  {
    id: "alert_005",
    customerId: "tesla",
    customerName: "Tesla",
    title: "Geographic drift detected",
    severity: "medium",
    severityLabel: "Medium Risk",
    driftType: "Geographic Drift",
    timestamp: "1h ago",
    explanation: "Counterparty jurisdiction shifted from CH to KY over last 30 days.",
  },
] as const;

function AlertsRouteShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });

  if (pathname === "/alerts" || pathname === "/alerts/") {
    return <AlertsPage />;
  }

  return <Outlet />;
}

function AlertsPage() {
  const navigate = useNavigate();

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1400px]">
        <header className="mb-6">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            Compliance queue
          </div>
          <h1 className="text-3xl font-display font-semibold">Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Sorted by severity. Open an alert to investigate.
          </p>
        </header>

        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate({ to: "/alerts/$id", params: { id: alert.id } })}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  navigate({ to: "/alerts/$id", params: { id: alert.id } });
                }
              }}
              className="group cursor-pointer rounded-xl border border-border bg-card glass px-4 py-3 grid grid-cols-[auto_1fr_auto] gap-4 items-center transition-all duration-200 hover:border-neon/50 hover:bg-surface-2/60 hover:shadow-[0_0_0_1px_oklch(0.92_0.22_128/0.18),0_8px_28px_-12px_oklch(0.92_0.22_128/0.25)] focus:outline-none focus:border-neon/60 lime-outline"
            >
              <AlertTriangle
                size={20}
                className={
                  alert.severity === "high"
                    ? "text-[color:var(--risk-high)]"
                    : alert.severity === "elevated"
                      ? "text-[color:var(--risk-elevated)]"
                      : "text-[color:var(--risk-medium)]"
                }
              />
              <div className="min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="font-medium truncate group-hover:text-neon transition-colors">
                    {alert.title}
                  </h3>
                  <RiskBadge level={alert.severity as RiskStatus} />
                  <span className="text-xs text-muted-foreground">{alert.severityLabel}</span>
                  <span className="text-xs text-muted-foreground">{alert.driftType}</span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  <Link
                    to="/customers/$id"
                    params={{ id: alert.customerId }}
                    onClick={(event) => event.stopPropagation()}
                    className="text-neon hover:underline"
                  >
                    {alert.customerName}
                  </Link>
                  {" · "}
                  {alert.timestamp} · {alert.explanation}
                </div>
              </div>
              <Link
                to="/alerts/$id"
                params={{ id: alert.id }}
                onClick={(event) => event.stopPropagation()}
                className="rounded-lg bg-neon-soft text-neon px-3 py-2 text-xs font-medium hover:bg-neon/25 hover:shadow-[0_0_18px_-4px_oklch(0.92_0.22_128/0.55)] transition-all inline-flex items-center gap-1.5"
              >
                Investigation <ArrowRight size={12} />
              </Link>
            </div>
          ))}
        </div>
      </div>
    </AppLayout>
  );
}
