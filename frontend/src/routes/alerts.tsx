import { createFileRoute, Link, Outlet, useNavigate, useRouterState } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { AlertTriangle, ArrowRight, Loader2 } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { RiskBadge } from "@/components/ui/risk-badge";
import { getAlerts } from "@/lib/services";
import type { Alert, RiskStatus } from "@/lib/types";

export const Route = createFileRoute("/alerts")({
  head: () => ({ meta: [{ title: "Alerts — HYDRA" }] }),
  component: AlertsRouteShell,
});

const sevOrder: Record<string, number> = { high: 0, elevated: 1, medium: 2, low: 3 };

function AlertsRouteShell() {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  if (pathname === "/alerts" || pathname === "/alerts/") return <AlertsPage />;
  return <Outlet />;
}

function AlertsPage() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAlerts()
      .then((a) => setAlerts([...a].sort((x, y) => (sevOrder[x.severity] ?? 9) - (sevOrder[y.severity] ?? 9))))
      .finally(() => setLoading(false));
  }, []);

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1400px]">
        <header className="mb-6">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            Compliance queue
          </div>
          <h1 className="text-3xl font-display font-semibold">Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Real-time drift events from Layer 1. Sorted by severity.
          </p>
        </header>

        {loading && (
          <div className="flex items-center gap-2 text-sm text-muted-foreground py-8">
            <Loader2 size={14} className="animate-spin" /> Fetching live alerts from pipeline…
          </div>
        )}

        {!loading && alerts.length === 0 && (
          <div className="rounded-xl border border-border bg-card glass px-5 py-8 text-center text-sm text-muted-foreground">
            No drift events detected yet. Trigger the pipeline to scan for new signals.
          </div>
        )}

        <div className="space-y-2">
          {alerts.map((alert) => (
            <div
              key={alert.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate({ to: "/alerts/$id", params: { id: alert.id } })}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); navigate({ to: "/alerts/$id", params: { id: alert.id } }); }
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
                  <span className="text-xs text-muted-foreground">{alert.driftType}</span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  <Link
                    to="/customers/$id"
                    params={{ id: alert.customerId }}
                    onClick={(e) => e.stopPropagation()}
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
                onClick={(e) => e.stopPropagation()}
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
