import type { RiskStatus } from "@/lib/types";

const map: Record<RiskStatus, { label: string; cls: string }> = {
  low: { label: "Low Risk", cls: "bg-[color:var(--risk-low)]/15 text-[color:var(--risk-low)] border-[color:var(--risk-low)]/30" },
  medium: { label: "Medium Risk", cls: "bg-[color:var(--risk-medium)]/15 text-[color:var(--risk-medium)] border-[color:var(--risk-medium)]/30" },
  elevated: { label: "Elevated Risk", cls: "bg-[color:var(--risk-elevated)]/15 text-[color:var(--risk-elevated)] border-[color:var(--risk-elevated)]/30" },
  high: { label: "High Risk", cls: "bg-[color:var(--risk-high)]/15 text-[color:var(--risk-high)] border-[color:var(--risk-high)]/30" },
};

export function RiskBadge({ level, label }: { level: RiskStatus; label?: string }) {
  const cfg = map[level];
  return (
    <span className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 text-[11px] font-medium ${cfg.cls}`}>
      <span className="h-1.5 w-1.5 rounded-full bg-current" />
      {label ?? cfg.label}
    </span>
  );
}
