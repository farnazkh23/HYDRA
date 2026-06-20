import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import { Search, SlidersHorizontal } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { CustomerFolderCard } from "@/components/CustomerFolderCard";
import { getCustomers } from "@/lib/services";
import type { Customer, DriftSeverity, RiskStatus } from "@/lib/types";

export const Route = createFileRoute("/customers/")({
  head: () => ({ meta: [{ title: "Customers — HYDRA" }] }),
  component: CustomersPage,
});

const riskOrder: Record<RiskStatus, number> = { high: 0, elevated: 1, medium: 2, low: 3 };
const driftOrder: Record<DriftSeverity, number> = { critical: 0, high: 1, medium: 2, low: 3 };

type SortKey = "risk" | "drift" | "volume" | "updated" | "newly";

function CustomersPage() {
  const [data, setData] = useState<Customer[]>([]);
  const [q, setQ] = useState("");
  const [sort, setSort] = useState<SortKey>("risk");
  const [riskFilter, setRiskFilter] = useState<"all" | RiskStatus>("all");
  const [driftFilter, setDriftFilter] = useState<"all" | DriftSeverity>("all");
  const [industry, setIndustry] = useState<string>("all");
  const [country, setCountry] = useState<string>("all");

  useEffect(() => {
    getCustomers().then(setData);
  }, []);

  const newlyOnboarded = useMemo(() => data.filter((c) => c.isNewlyOnboarded), [data]);
  const industries = useMemo(
    () => Array.from(new Set(data.map((c) => c.industry))).sort(),
    [data],
  );
  const countries = useMemo(
    () => Array.from(new Set(data.map((c) => c.country))).sort(),
    [data],
  );

  const filtered = useMemo(() => {
    let r = data.slice();
    if (riskFilter !== "all") r = r.filter((c) => c.riskStatus === riskFilter);
    if (driftFilter !== "all") r = r.filter((c) => c.driftSeverity === driftFilter);
    if (industry !== "all") r = r.filter((c) => c.industry === industry);
    if (country !== "all") r = r.filter((c) => c.country === country);
    if (q) {
      const s = q.toLowerCase();
      r = r.filter(
        (c) =>
          c.companyName.toLowerCase().includes(s) ||
          c.responsiblePerson.toLowerCase().includes(s),
      );
    }
    switch (sort) {
      case "risk":
        r.sort((a, b) => riskOrder[a.riskStatus] - riskOrder[b.riskStatus]);
        break;
      case "drift":
        r.sort((a, b) => driftOrder[a.driftSeverity] - driftOrder[b.driftSeverity]);
        break;
      case "volume":
        r.sort((a, b) => parseVol(b.transactionVolume) - parseVol(a.transactionVolume));
        break;
      case "updated":
        r.sort((a, b) => parseUpdated(a.lastUpdated) - parseUpdated(b.lastUpdated));
        break;
      case "newly":
        r.sort((a, b) => Number(!!b.isNewlyOnboarded) - Number(!!a.isNewlyOnboarded));
        break;
    }
    return r;
  }, [data, q, sort, riskFilter, driftFilter, industry, country]);

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1600px]">
        <header className="mb-8">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">
            Case folders
          </div>
          <h1 className="text-3xl font-display font-semibold">Customers</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Monitor customer folders, profile-building clients, and active KYC drift cases.
          </p>
        </header>

        {/* Newly onboarded */}
        <section className="mb-10">
          <div className="flex items-end justify-between mb-3">
            <div>
              <h2 className="font-display text-lg font-semibold">
                Newly Onboarded <span className="text-neon">— Profile Building</span>
              </h2>
              <p className="text-xs text-muted-foreground mt-0.5">
                Baseline risk profile still being built by HYDRA.
              </p>
            </div>
            <span className="text-xs text-muted-foreground">
              {newlyOnboarded.length} customers
            </span>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {newlyOnboarded.map((c) => (
              <CustomerFolderCard key={c.id} customer={c} variant="onboarding" />
            ))}
          </div>
        </section>

        {/* Filter / sort bar */}
        <section className="mb-5">
          <div className="flex items-center gap-2 mb-3 text-xs uppercase tracking-[0.18em] text-muted-foreground">
            <SlidersHorizontal size={13} />
            Filter & sort
          </div>
          <div className="rounded-xl border border-border bg-card/60 glass p-3 flex flex-wrap items-center gap-2">
            <div className="relative flex-1 min-w-[220px] max-w-sm">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground" />
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                placeholder="Search company or responsible person…"
                className="w-full rounded-lg border border-border bg-surface-2 pl-9 pr-3 py-2 text-sm placeholder:text-muted-foreground focus:outline-none focus:border-neon/50"
              />
            </div>
            <Select
              label="Risk"
              value={riskFilter}
              onChange={(v) => setRiskFilter(v as typeof riskFilter)}
              options={[
                { v: "all", l: "All" },
                { v: "low", l: "Low" },
                { v: "medium", l: "Medium" },
                { v: "elevated", l: "Elevated" },
                { v: "high", l: "High" },
              ]}
            />
            <Select
              label="Drift"
              value={driftFilter}
              onChange={(v) => setDriftFilter(v as typeof driftFilter)}
              options={[
                { v: "all", l: "All" },
                { v: "low", l: "Low" },
                { v: "medium", l: "Medium" },
                { v: "high", l: "High" },
                { v: "critical", l: "Critical" },
              ]}
            />
            <Select
              label="Industry"
              value={industry}
              onChange={setIndustry}
              options={[{ v: "all", l: "All" }, ...industries.map((i) => ({ v: i, l: i }))]}
            />
            <Select
              label="Country"
              value={country}
              onChange={setCountry}
              options={[{ v: "all", l: "All" }, ...countries.map((i) => ({ v: i, l: i }))]}
            />
            <div className="ml-auto" />
            <Select
              label="Sort"
              value={sort}
              onChange={(v) => setSort(v as SortKey)}
              options={[
                { v: "risk", l: "Highest risk" },
                { v: "drift", l: "Highest drift" },
                { v: "volume", l: "Transaction volume" },
                { v: "updated", l: "Last updated" },
                { v: "newly", l: "Newly onboarded" },
              ]}
            />
          </div>
        </section>

        <div className="flex items-center justify-between mb-3">
          <h2 className="font-display text-lg font-semibold">
            All Customers <span className="text-muted-foreground font-normal">— {filtered.length}</span>
          </h2>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-5 pt-1">
          {filtered.map((c) => (
            <CustomerFolderCard key={c.id} customer={c} />
          ))}
          {filtered.length === 0 && (
            <div className="col-span-full rounded-xl border border-dashed border-border p-10 text-center text-sm text-muted-foreground">
              No customers match the current filters.
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}

function parseVol(s: string) {
  const n = parseFloat(s.replace(/[^\d.]/g, ""));
  if (/B/i.test(s)) return n * 1e9;
  if (/M/i.test(s)) return n * 1e6;
  if (/K/i.test(s)) return n * 1e3;
  return n;
}

function parseUpdated(s: string) {
  const m = s.match(/(\d+)\s*(min|h|d)/i);
  if (!m) return 9999;
  const n = parseInt(m[1], 10);
  const unit = m[2].toLowerCase();
  if (unit === "h") return n * 60;
  if (unit === "d") return n * 60 * 24;
  return n;
}

function Select({
  label,
  value,
  onChange,
  options,
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  options: { v: string; l: string }[];
}) {
  return (
    <label className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm">
      <span className="text-muted-foreground text-xs">{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="bg-transparent outline-none text-foreground max-w-[160px]"
      >
        {options.map((o) => (
          <option key={o.v} value={o.v} className="bg-surface">
            {o.l}
          </option>
        ))}
      </select>
    </label>
  );
}
