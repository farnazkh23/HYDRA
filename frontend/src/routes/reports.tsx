import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Download, FileText, User, CheckCircle2, Sparkles } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RiskBadge } from "@/components/ui/risk-badge";
import type { RiskStatus, DriftSeverity } from "@/lib/types";

export const Route = createFileRoute("/reports")({
  head: () => ({ meta: [{ title: "Reports — HYDRA" }] }),
  component: ReportsPage,
});

type ReportCard = {
  id: string;
  title: string;
  desc: string;
  last: string;
  category: string;
};

const riskReports: ReportCard[] = [
  {
    id: "high",
    title: "High-risk clients report",
    desc: "All customers with risk score ≥ 80 in the last 30 days.",
    last: "Today, 09:12",
    category: "risk",
  },
  {
    id: "medium",
    title: "Medium-risk clients report",
    desc: "Watchlist for medium-tier exposure shifts.",
    last: "Today, 06:00",
    category: "risk",
  },
  {
    id: "low",
    title: "Low-risk clients report",
    desc: "Stable baseline customers — confirmation only.",
    last: "Yesterday, 18:30",
    category: "risk",
  },
];

const specialistReports: ReportCard[] = [
  {
    id: "kyc",
    title: "KYC drift summary report",
    desc: "Field-level baseline vs live-risk drift across monitored customers.",
    last: "Today, 04:00",
    category: "specialist",
  },
  {
    id: "gov",
    title: "Governance audit report",
    desc: "Human review actions, approval states, and escalation history.",
    last: "Today, 02:00",
    category: "specialist",
  },
  {
    id: "cost",
    title: "Heavy AI usage / cost report",
    desc: "Router decisions, heavy-model invocations, token usage, and estimated cost.",
    last: "Today, 01:30",
    category: "specialist",
  },
];

type CustomerOption = {
  id: string;
  name: string;
  risk: RiskStatus;
  drift: DriftSeverity;
  lastUpdated: string;
};

const customerOptions: CustomerOption[] = [
  { id: "spacex", name: "SpaceX", risk: "high", drift: "critical", lastUpdated: "2h ago" },
  { id: "tesla", name: "Tesla", risk: "elevated", drift: "high", lastUpdated: "5h ago" },
  { id: "amazon", name: "Amazon", risk: "medium", drift: "medium", lastUpdated: "1d ago" },
  { id: "nvidia", name: "NVIDIA", risk: "medium", drift: "low", lastUpdated: "3h ago" },
  { id: "binance", name: "Binance Holdings", risk: "high", drift: "critical", lastUpdated: "1h ago" },
  { id: "openai", name: "OpenAI", risk: "elevated", drift: "high", lastUpdated: "6h ago" },
  { id: "apple", name: "Apple", risk: "low", drift: "low", lastUpdated: "2d ago" },
  { id: "meta", name: "Meta", risk: "medium", drift: "medium", lastUpdated: "8h ago" },
];

const driftLabel: Record<DriftSeverity, string> = {
  low: "Low drift",
  medium: "Medium drift",
  high: "High drift",
  critical: "Critical drift",
};

const driftClass: Record<DriftSeverity, string> = {
  low: "text-[color:var(--risk-low)] border-[color:var(--risk-low)]/30 bg-[color:var(--risk-low)]/10",
  medium: "text-[color:var(--risk-medium)] border-[color:var(--risk-medium)]/30 bg-[color:var(--risk-medium)]/10",
  high: "text-[color:var(--risk-elevated)] border-[color:var(--risk-elevated)]/30 bg-[color:var(--risk-elevated)]/10",
  critical: "text-[color:var(--risk-high)] border-[color:var(--risk-high)]/30 bg-[color:var(--risk-high)]/10",
};

function triggerDownload(filename: string, payload: unknown) {
  const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

function slug(s: string) {
  return s.toLowerCase().replace(/[^a-z0-9]+/g, "_").replace(/^_|_$/g, "");
}

function ReportTile({ r }: { r: ReportCard }) {
  const download = () => {
    triggerDownload(`hydra_${slug(r.title)}.json`, {
      report_id: r.id,
      title: r.title,
      report_type: r.category,
      generated_at: new Date().toISOString(),
      note: "Mock HYDRA report — replace with live API output.",
    });
  };
  return (
    <div className="rounded-2xl border border-border bg-card glass p-5 flex flex-col">
      <div className="h-10 w-10 rounded-lg bg-neon-soft text-neon grid place-items-center mb-3">
        <FileText size={18} />
      </div>
      <h3 className="font-display font-semibold">{r.title}</h3>
      <p className="text-sm text-muted-foreground mt-1 flex-1">{r.desc}</p>
      <div className="mt-4 flex items-center justify-between">
        <span className="text-[11px] text-muted-foreground">Last: {r.last}</span>
        <button
          onClick={download}
          className="inline-flex items-center gap-1.5 rounded-lg bg-neon-soft text-neon px-3 py-2 text-xs font-medium hover:bg-neon/25"
        >
          <Download size={12} /> Download
        </button>
      </div>
    </div>
  );
}

function SectionHeader({ kicker, title, desc }: { kicker: string; title: string; desc?: string }) {
  return (
    <div className="mb-4">
      <div className="text-[11px] uppercase tracking-[0.2em] text-muted-foreground mb-1">
        {kicker}
      </div>
      <h2 className="text-lg font-display font-semibold">{title}</h2>
      {desc && <p className="text-xs text-muted-foreground mt-1">{desc}</p>}
    </div>
  );
}

function CustomerReportCard() {
  const [customerId, setCustomerId] = useState<string>("");
  const [prepared, setPrepared] = useState<string | null>(null);
  const selected = customerOptions.find((c) => c.id === customerId);

  const generate = () => {
    if (!selected) return;
    setPrepared(selected.id);
  };

  const download = () => {
    if (!selected) return;
    triggerDownload(`hydra_customer_${slug(selected.name)}_report.json`, {
      report_id: `customer_${selected.id}`,
      title: `Customer-specific report — ${selected.name}`,
      report_type: "customer",
      customer: {
        id: selected.id,
        name: selected.name,
        risk_status: selected.risk,
        drift_severity: selected.drift,
        last_updated: selected.lastUpdated,
      },
      generated_at: new Date().toISOString(),
      note: "Mock HYDRA customer-specific report — replace with live API output.",
    });
  };

  const isPrepared = prepared && selected && prepared === selected.id;

  return (
    <div className="rounded-2xl border border-border bg-card glass p-6 relative overflow-hidden">
      <div className="absolute -top-16 -right-16 h-48 w-48 rounded-full bg-neon/10 blur-3xl pointer-events-none" />
      <div className="flex items-start gap-4 mb-5">
        <div className="h-11 w-11 rounded-lg bg-neon-soft text-neon grid place-items-center">
          <User size={20} />
        </div>
        <div className="flex-1">
          <h3 className="font-display font-semibold text-lg">Customer-specific report</h3>
          <p className="text-sm text-muted-foreground mt-1">
            Generate an audit-ready report for one selected customer.
          </p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-[1fr_auto] gap-4 items-end">
        <div>
          <label className="text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            Select customer
          </label>
          <div className="mt-1.5">
            <Select
              value={customerId}
              onValueChange={(v) => {
                setCustomerId(v);
                setPrepared(null);
              }}
            >
              <SelectTrigger className="bg-background/40 border-border">
                <SelectValue placeholder="Choose a customer…" />
              </SelectTrigger>
              <SelectContent>
                {customerOptions.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>
        </div>

        <button
          onClick={generate}
          disabled={!selected || !!isPrepared}
          className="inline-flex items-center justify-center gap-1.5 rounded-lg bg-neon text-[#0b0f0a] px-4 py-2 text-xs font-semibold hover:bg-neon/90 disabled:opacity-40 disabled:cursor-not-allowed h-9"
        >
          <Sparkles size={12} /> Generate report
        </button>
      </div>

      {selected && (
        <div className="mt-5 flex flex-wrap items-center gap-2 text-[11px]">
          <RiskBadge level={selected.risk} />
          <span
            className={`inline-flex items-center gap-1.5 rounded-md border px-2 py-0.5 font-medium ${driftClass[selected.drift]}`}
          >
            <span className="h-1.5 w-1.5 rounded-full bg-current" />
            {driftLabel[selected.drift]}
          </span>
          <span className="text-muted-foreground">Last updated {selected.lastUpdated}</span>
        </div>
      )}

      <div className="mt-5 pt-5 border-t border-border/60 flex items-center justify-between gap-3 min-h-[40px]">
        {isPrepared ? (
          <div className="inline-flex items-center gap-2 text-xs text-neon">
            <CheckCircle2 size={14} />
            Report prepared for {selected!.name}
          </div>
        ) : (
          <span className="text-[11px] text-muted-foreground">
            {selected
              ? "Click Generate report to prepare the export."
              : "Select a customer to begin."}
          </span>
        )}
        <button
          onClick={download}
          disabled={!isPrepared}
          className="inline-flex items-center gap-1.5 rounded-lg bg-neon-soft text-neon px-3 py-2 text-xs font-medium hover:bg-neon/25 disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Download size={12} /> Download
        </button>
      </div>
    </div>
  );
}

function ReportsPage() {
  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1400px]">
        <header className="mb-8">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            Exports
          </div>
          <h1 className="text-3xl font-display font-semibold">Reports</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Download HYDRA reports for compliance review.
          </p>
        </header>

        <section className="mb-10">
          <SectionHeader
            kicker="01 — By risk level"
            title="Reports by risk level"
            desc="Predefined population cuts across the monitored portfolio."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {riskReports.map((r) => (
              <ReportTile key={r.id} r={r} />
            ))}
          </div>
        </section>

        <section className="mb-10">
          <SectionHeader
            kicker="02 — By customer"
            title="Report by customer"
            desc="Audit-ready export for a single selected client."
          />
          <CustomerReportCard />
        </section>

        <section>
          <SectionHeader
            kicker="03 — Specialist"
            title="Specialist reports"
            desc="System-level digests across the HYDRA engine."
          />
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {specialistReports.map((r) => (
              <ReportTile key={r.id} r={r} />
            ))}
          </div>
        </section>
      </div>
    </AppLayout>
  );
}
