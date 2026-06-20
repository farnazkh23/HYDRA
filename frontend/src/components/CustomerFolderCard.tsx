import { Link } from "@tanstack/react-router";
import { ArrowUpRight, TrendingDown, TrendingUp, Minus, FolderOpen } from "lucide-react";
import type { Customer, DriftSeverity } from "@/lib/types";
import { RiskBadge } from "@/components/ui/risk-badge";

const trendIcon = { up: TrendingUp, down: TrendingDown, flat: Minus };

const driftMap: Record<DriftSeverity, { label: string; cls: string }> = {
  low: { label: "Low Drift", cls: "bg-[color:var(--risk-low)]/15 text-[color:var(--risk-low)] border-[color:var(--risk-low)]/30" },
  medium: { label: "Medium Drift", cls: "bg-[color:var(--risk-medium)]/15 text-[color:var(--risk-medium)] border-[color:var(--risk-medium)]/30" },
  high: { label: "High Drift", cls: "bg-[color:var(--risk-elevated)]/15 text-[color:var(--risk-elevated)] border-[color:var(--risk-elevated)]/30" },
  critical: { label: "Critical Drift", cls: "bg-[color:var(--risk-high)]/15 text-[color:var(--risk-high)] border-[color:var(--risk-high)]/30" },
};

function DriftBadge({ level }: { level: DriftSeverity }) {
  const cfg = driftMap[level];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium ${cfg.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {cfg.label}
    </span>
  );
}

export function CustomerFolderCard({
  customer,
  variant = "default",
}: {
  customer: Customer;
  variant?: "default" | "onboarding";
}) {
  const TIcon = trendIcon[customer.trend];
  const initials = customer.companyName.slice(0, 2).toUpperCase();

  return (
    <Link to="/customers/$id" params={{ id: customer.id }} className="group relative block pt-2">
      {/* Folder tab */}
      <div className="absolute top-0 left-5 h-3 w-24 rounded-t-md bg-surface-2 border border-b-0 border-border" />
      <div className="relative rounded-xl border border-border bg-card glass p-4 transition-all group-hover:border-neon/40 group-hover:shadow-[0_0_0_1px_oklch(0.92_0.22_128/0.3),0_12px_40px_-12px_oklch(0.92_0.22_128/0.25)] lime-outline">
        <div className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-neon/60 to-transparent" />

        <div className="flex items-start gap-3">
          <div className="h-11 w-11 rounded-lg bg-surface-2 border border-border grid place-items-center text-sm font-semibold text-neon shrink-0">
            {initials}
          </div>
          <div className="min-w-0 flex-1">
            <div className="flex items-center gap-2">
              <h3 className="font-display text-base font-semibold truncate">{customer.companyName}</h3>
              {variant === "default" && (
                <TIcon
                  size={14}
                  className={
                    customer.trend === "up"
                      ? "text-[color:var(--risk-elevated)]"
                      : customer.trend === "down"
                      ? "text-[color:var(--risk-low)]"
                      : "text-muted-foreground"
                  }
                />
              )}
            </div>
            <div className="text-xs text-muted-foreground truncate">{customer.responsiblePerson}</div>
          </div>
          <ArrowUpRight size={16} className="text-muted-foreground group-hover:text-neon transition" />
        </div>

        <div className="mt-3 flex flex-wrap items-center gap-1.5">
          {variant === "onboarding" ? (
            <>
              <span className="inline-flex items-center gap-1.5 rounded-md border border-neon/30 bg-neon-soft px-2 py-0.5 text-[11px] font-medium text-neon">
                <FolderOpen size={11} />
                Profile building active
              </span>
              <span className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-[11px] text-muted-foreground">
                Risk monitoring
              </span>
            </>
          ) : (
            <>
              <RiskBadge level={customer.riskStatus} />
              <DriftBadge level={customer.driftSeverity} />
            </>
          )}
        </div>

        <div className="mt-4 flex items-center justify-between text-[11px] text-muted-foreground border-t border-border pt-3">
          <span>Updated {customer.lastUpdated}</span>
          <span className="text-neon font-medium">Open profile →</span>
        </div>
      </div>
    </Link>
  );
}
