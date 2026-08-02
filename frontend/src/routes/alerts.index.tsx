import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { AlertTriangle, ArrowRight } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { RiskBadge } from "@/components/ui/risk-badge";
import { getAlerts } from "@/lib/services";
import type { Alert, RiskStatus } from "@/lib/types";

export const Route = createFileRoute("/alerts/")({
  head: () => ({ meta: [{ title: "Alerts — HYDRA" }] }),
  component: AlertsPage,
});

const sevOrder: Record<string, number> = { high: 0, elevated: 1, medium: 2, low: 3 };

function AlertsPage() {
  const navigate = useNavigate();
  const [allAlerts, setAllAlerts] = useState<Alert[]>([]);

  useEffect(() => {
    getAlerts().then(setAllAlerts);
  }, []);

  const alerts = useMemo(
    () =>
      [...allAlerts].sort(
        (x, y) => (sevOrder[x.severity] ?? 9) - (sevOrder[y.severity] ?? 9),
      ),
    [allAlerts],
  );

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1400px]">
        <header className="mb-6">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            Compliance queue
          </div>
          <h1 className="text-3xl font-display font-semibold">Alerts</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Sorted by severity. Click a row to open the full investigation.
          </p>
        </header>

        <div className="space-y-2">
          {alerts.map((a) => (
            <div
              key={a.id}
              data-alert-row={a.id}
              role="button"
              tabIndex={0}
              onClick={() => navigate({ to: "/alerts/$id", params: { id: a.id } })}
              onKeyDown={(e) => {
                if (e.key === "Enter" || e.key === " ") {
                  e.preventDefault();
                  navigate({ to: "/alerts/$id", params: { id: a.id } });
                }
              }}
              className="group cursor-pointer rounded-xl border border-border bg-card glass px-4 py-3 grid grid-cols-[auto_1fr_auto] gap-4 items-center transition-all duration-200 hover:border-neon/50 hover:bg-surface-2/60 hover:shadow-[0_0_0_1px_oklch(0.92_0.22_128/0.18),0_8px_28px_-12px_oklch(0.92_0.22_128/0.25)] focus:outline-none focus:border-neon/60"
            >
              <AlertTriangle
                size={20}
                className={
                  a.severity === "high"
                    ? "text-[color:var(--risk-high)]"
                    : a.severity === "elevated"
                      ? "text-[color:var(--risk-elevated)]"
                      : "text-[color:var(--risk-medium)]"
                }
              />
              <div className="min-w-0">
                <div className="flex items-center gap-3 flex-wrap">
                  <h3 className="font-medium truncate group-hover:text-neon transition-colors">
                    {a.title}
                  </h3>
                  <RiskBadge level={a.severity as RiskStatus} />
                  <span className="text-xs text-muted-foreground">{a.driftType}</span>
                </div>
                <div className="text-xs text-muted-foreground mt-0.5">
                  <Link
                    to="/customers/$id"
                    params={{ id: a.customerId }}
                    onClick={(e) => e.stopPropagation()}
                    className="text-neon hover:underline"
                  >
                    {a.customerName}
                  </Link>
                  {" · "}
                  {a.timestamp} · {a.explanation}
                </div>
              </div>
              <Link
                to="/alerts/$id"
                params={{ id: a.id }}
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
