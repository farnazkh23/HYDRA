import { createFileRoute, Link } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import {
  ArrowLeft, BadgeCheck, Building2, MapPin, Calendar, ShieldCheck,
  TrendingUp, AlertTriangle, Download, MoreHorizontal,
  Globe2, ArrowLeftRight, UserPlus, Activity, ChevronRight,
} from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { RiskBadge } from "@/components/ui/risk-badge";
import { getCustomerById, getKYCDriftRecord, getReasoningTrace, getAlerts, getKGTriples } from "@/lib/services";
import type { Customer, KYCDriftRecord, AIReasoningTrace, Alert, RiskStatus } from "@/lib/types";

export const Route = createFileRoute("/customers/$id")({
  head: ({ params }) => ({ meta: [{ title: `${params.id} — HYDRA` }] }),
  component: CustomerDetail,
});

const driftPoints = [22, 28, 31, 30, 38, 44, 50, 55, 60, 64, 68, 75, 81];

function CustomerDetail() {
  const { id } = Route.useParams();
  const [c, setC] = useState<Customer | null>(null);
  const [drift, setDrift] = useState<KYCDriftRecord | null>(null);
  const [trace, setTrace] = useState<AIReasoningTrace | null>(null);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [kgTriples, setKgTriples] = useState<Array<{ subject: string; predicate: string; object: string; start_time: string }>>([]);

  useEffect(() => {
    getCustomerById(id).then((x) => setC(x ?? null));
    getKYCDriftRecord(id).then((x) => setDrift(x ?? null));
    getKGTriples(id).then((t) => setKgTriples(t ?? []));
  }, [id]);

  useEffect(() => {
    if (!c) return;
    getAlerts().then((a) => {
      // customerId in alerts is clientId ("demo-spacex-001"), match via c.clientId
      const customerAlerts = a.filter((x) => x.customerId === c.clientId || x.customerId === id);
      setAlerts(customerAlerts);
      if (customerAlerts[0]) {
        getReasoningTrace(customerAlerts[0].id).then((x) => setTrace(x ?? null));
      }
    });
  }, [c]);

  if (!c) return <AppLayout><div className="p-10 text-muted-foreground">Loading…</div></AppLayout>;

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1600px]">
        {/* Header */}
        <div className="flex items-center justify-between gap-4 mb-5 flex-wrap">
          <Link to="/customers" className="inline-flex items-center gap-2 text-sm text-neon hover:underline">
            <ArrowLeft size={16} /> Back to Customers
          </Link>
          <div className="flex gap-2">
            <button className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-2 text-sm hover:border-neon/40">
              <Download size={14} /> Export
            </button>
            <button className="inline-flex items-center justify-center rounded-lg border border-border bg-surface-2 h-9 w-9 hover:border-neon/40">
              <MoreHorizontal size={16} />
            </button>
          </div>
        </div>

        <div className="flex items-start justify-between gap-6 flex-wrap mb-6">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="font-display text-4xl font-semibold">{c.companyName}</h1>
              <BadgeCheck size={22} className="text-neon" />
            </div>
            <div className="mt-1 text-sm text-muted-foreground">
              Customer ID: <span className="text-foreground/80">C-54871</span> · {c.companyType}
            </div>
            <div className="mt-2 inline-flex items-center gap-2 text-[11px] text-muted-foreground">
              <span className="h-1.5 w-1.5 rounded-full bg-neon animate-pulse" />
              Last updated 2 min ago · Live drift recalculation active
            </div>
          </div>

          <div className="rounded-2xl border border-border bg-card glass px-5 py-4 grid grid-cols-2 md:grid-cols-4 gap-6">
            <MiniMeta icon={Building2} label="Industry" value={c.industry} />
            <MiniMeta icon={MapPin} label="Country" value={c.country} />
            <MiniMeta icon={Calendar} label="Onboarded" value={c.onboardedDate} />
            <MiniMeta icon={ShieldCheck} label="KYC Status" valueNode={
              <span className="inline-flex items-center gap-1.5 rounded-md bg-neon-soft text-neon px-2 py-0.5 text-xs">
                {c.kycStatus}
              </span>
            } />
          </div>
        </div>

        {/* Main grid */}
        <div className="grid grid-cols-12 gap-5">
          {/* Left: profile */}
          <div className="col-span-12 lg:col-span-4 space-y-5">
            <Card title="Company Profile">
              <div className="flex flex-col items-center text-center pb-4 border-b border-border">
                <div className="h-20 w-20 rounded-full border border-border bg-surface-2 grid place-items-center">
                  <Building2 size={32} className="text-muted-foreground" />
                </div>
                <div className="mt-3 font-display text-lg font-semibold">{c.companyName}</div>
              </div>
              <dl className="mt-4 space-y-2.5 text-sm">
                <KV k="Legal Name" v={c.legalName} />
                <KV k="Registration No." v="HRB 123456" />
                <KV k="VAT / Tax ID" v="US-DEMO-987654" />
                <KV k="Industry" v={c.industry} />
                <KV k="Website" v={<a className="text-neon hover:underline" href="#">www.spacex.com</a>} />
              </dl>
            </Card>

            <Card title="Responsible Person" icon={<UserPlus size={14} />}>
              <div className="flex items-center gap-3">
                <div className="h-11 w-11 rounded-full bg-neon/20 grid place-items-center text-sm font-semibold text-neon">
                  {c.responsiblePerson.split(" ").map((p) => p[0]).join("").slice(0,2)}
                </div>
                <div>
                  <div className="text-sm font-semibold">{c.responsiblePerson}</div>
                  <div className="text-xs text-muted-foreground">{c.responsiblePersonRole}</div>
                </div>
              </div>
              <dl className="mt-4 space-y-2.5 text-sm">
                <KV k="Email" v={<span className="text-neon">elon.musk@spacex.com</span>} />
                <KV k="Phone" v="+1 555 0199" />
                <KV k="LinkedIn" v={<span className="text-neon">linkedin.com/in/demo-elon-musk</span>} />
              </dl>
            </Card>

            <Card title="Financial Overview">
              <dl className="space-y-2.5 text-sm">
                <KV k="Net Worth" v="$ 24.8B" />
                <KV k="Share Capital" v="$ 8.5B" />
                <KV k="Investments" v="$ 12.3B" />
                <KV k="Total Loans" v="$ 5.7B" />
                <KV k="Transaction Volume" v={c.transactionVolume} />
              </dl>
              <button className="mt-4 w-full rounded-lg bg-neon-soft text-neon py-2 text-sm font-medium hover:bg-neon/25 inline-flex items-center justify-center gap-1">
                View full profile <ChevronRight size={14} />
              </button>
            </Card>
          </div>

          {/* Middle/right */}
          <div className="col-span-12 lg:col-span-8 space-y-5">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Risk Score */}
              <Card title="Risk Score">
                <div className="flex items-end gap-3">
                  <div className="font-display text-5xl font-semibold text-neon">{c.riskScore}</div>
                  <RiskBadge level={c.riskStatus} />
                </div>
                <div className="mt-2 text-xs text-[color:var(--risk-elevated)]">
                  ↑ 32 points (65%) <span className="text-muted-foreground">vs 30 days ago</span>
                </div>
                <Sparkline values={driftPoints} className="mt-4 h-28 w-full" />
                <div className="mt-1 flex justify-between text-[10px] text-muted-foreground">
                  <span>Mar 15</span><span>Apr 15</span><span>May 15</span><span>Jun 12</span>
                </div>
              </Card>

              {/* Overall Drift */}
              <Card title="Overall Drift">
                <DriftGauge value={c.driftPercent} />
                <div className="text-center text-xs text-[color:var(--risk-elevated)] mt-2">
                  ↑ 18% <span className="text-muted-foreground">vs 30 days ago</span>
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Detected Drifts */}
              <Card title="Detected Drifts" action="View all">
                <ul className="space-y-3">
                  <DriftRow icon={Globe2} label="Geographic Drift" sev="high" delta="+28" />
                  <DriftRow icon={ArrowLeftRight} label="Transaction Drift" sev="elevated" delta="+17" />
                  <DriftRow icon={UserPlus} label="Ownership Drift" sev="elevated" delta="+12" />
                  <DriftRow icon={Activity} label="Behavioral Drift" sev="low" delta="+5" />
                </ul>
              </Card>

              {/* Verification */}
              <Card title="Verification Status">
                <div className="flex items-center gap-5">
                  <VerificationDonut completed={7} total={9} />
                  <ul className="text-sm space-y-1.5 flex-1">
                    {[
                      ["Identity Verification", true],
                      ["Address Verification", true],
                      ["UBO Verification", true],
                      ["Sanctions Screening", true],
                      ["PEP Screening", true],
                      ["Transaction Monitoring", true],
                      ["Media Check", false],
                      ["Document Verification", false],
                      ["Risk Assessment", true],
                    ].map(([l, ok]) => (
                      <li key={String(l)} className="flex items-center justify-between gap-3">
                        <span className="text-foreground/80">{l as string}</span>
                        <span className={`h-4 w-4 rounded-full grid place-items-center text-[10px] ${ok ? "bg-neon/20 text-neon" : "border border-border text-muted-foreground"}`}>
                          {ok ? "✓" : ""}
                        </span>
                      </li>
                    ))}
                  </ul>
                </div>
              </Card>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
              {/* Exposure */}
              <Card title="Exposure Summary">
                <div className="grid grid-cols-2 gap-3">
                  <Mini label="Total Exposure" v="$ 5.7B" />
                  <Mini label="Outstanding Loans" v="$ 3.2B" />
                  <Mini label="Investments" v="$ 2.1B" />
                  <Mini label="Utilization Rate" v="42%" />
                </div>
              </Card>

              {/* Recent Alerts */}
              <Card title="Recent Alerts" action="View all">
                <ul className="space-y-3">
                  {(alerts.length ? alerts : [
                    { id: "x1", title: "High geographic drift detected", timestamp: "2h ago", severity: "high" as const },
                    { id: "x2", title: "Transaction pattern anomaly", timestamp: "1d ago", severity: "elevated" as const },
                    { id: "x3", title: "New beneficial owner identified", timestamp: "2d ago", severity: "high" as const },
                  ]).slice(0, 4).map((a) => (
                    <li key={a.id} className="flex items-start gap-3">
                      <AlertTriangle size={16} className={sevText((a as Alert).severity ?? "high")} />
                      <div className="flex-1 min-w-0">
                        <div className="text-sm font-medium truncate">{a.title}</div>
                      </div>
                      <span className="text-[11px] text-muted-foreground shrink-0">{a.timestamp}</span>
                    </li>
                  ))}
                </ul>
              </Card>
            </div>

            {/* Engine Analysis */}
            {trace && <EngineAnalysis trace={trace} />}

            {/* Live KG Triples from Neo4j */}
            {kgTriples.length > 0 && (
              <section className="rounded-2xl border border-border bg-card glass p-5">
                <h3 className="text-sm font-semibold mb-1">Knowledge Graph — Active Relationships</h3>
                <p className="text-[11px] text-muted-foreground mb-4">Live entity triples from Neo4j updated by HYDRA drift events.</p>
                <div className="overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="border-b border-border text-muted-foreground text-left">
                        <th className="pb-2 pr-4 font-medium">Subject</th>
                        <th className="pb-2 pr-4 font-medium">Relationship</th>
                        <th className="pb-2 pr-4 font-medium">Object</th>
                        <th className="pb-2 font-medium">Since</th>
                      </tr>
                    </thead>
                    <tbody>
                      {kgTriples.map((t, i) => (
                        <tr key={i} className="border-b border-border/50 hover:bg-surface-2/40">
                          <td className="py-2 pr-4 text-foreground/80">{t.subject}</td>
                          <td className="py-2 pr-4">
                            <span className="rounded-md bg-neon-soft text-neon px-2 py-0.5 font-mono text-[10px]">
                              {t.predicate.replace(/_/g, " ")}
                            </span>
                          </td>
                          <td className="py-2 pr-4 text-foreground/80">{t.object}</td>
                          <td className="py-2 text-muted-foreground">{t.start_time ? new Date(t.start_time).toLocaleDateString() : "—"}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </section>
            )}

            {/* KYC Drift Diff */}
            {drift && <KYCDriftCard record={drift} />}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}

/* ---------------- small parts ---------------- */

function Card({ title, action, icon, children }: { title: string; action?: string; icon?: React.ReactNode; children: React.ReactNode }) {
  return (
    <section className="rounded-2xl border border-border bg-card glass p-5">
      <header className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold tracking-wide flex items-center gap-2">
          {icon && <span className="text-muted-foreground">{icon}</span>}
          {title}
        </h3>
        {action && <button className="text-xs text-neon hover:underline">{action}</button>}
      </header>
      {children}
    </section>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-3 text-sm">
      <dt className="text-muted-foreground text-xs">{k}</dt>
      <dd className="text-foreground/90 text-right">{v}</dd>
    </div>
  );
}

function MiniMeta({ icon: Icon, label, value, valueNode }: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; value?: string; valueNode?: React.ReactNode }) {
  return (
    <div className="flex items-center gap-3 min-w-[140px]">
      <div className="h-9 w-9 rounded-lg bg-surface-2 border border-border grid place-items-center">
        <Icon size={16} className="text-muted-foreground" />
      </div>
      <div className="min-w-0">
        <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
        <div className="text-sm font-medium truncate">{valueNode ?? value}</div>
      </div>
    </div>
  );
}

function Mini({ label, v }: { label: string; v: string }) {
  return (
    <div className="rounded-xl border border-border bg-surface-2/60 p-3">
      <div className="text-[11px] text-muted-foreground">{label}</div>
      <div className="font-display text-lg font-semibold text-neon mt-0.5">{v}</div>
    </div>
  );
}

function sevText(s: RiskStatus) {
  return s === "high" ? "text-[color:var(--risk-high)]"
    : s === "elevated" ? "text-[color:var(--risk-elevated)]"
    : s === "medium" ? "text-[color:var(--risk-medium)]" : "text-[color:var(--risk-low)]";
}

function DriftRow({ icon: Icon, label, sev, delta }: { icon: React.ComponentType<{ size?: number; className?: string }>; label: string; sev: RiskStatus; delta: string }) {
  const sevLabel = sev === "high" ? "High Impact" : sev === "elevated" ? "Elevated" : sev === "medium" ? "Medium" : "Low Impact";
  return (
    <li className="flex items-center gap-3">
      <div className={`h-9 w-9 rounded-lg grid place-items-center border ${sevBgBorder(sev)}`}>
        <Icon size={16} className={sevText(sev)} />
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-sm font-medium">{label}</div>
        <div className="mt-0.5"><RiskBadge level={sev} label={sevLabel} /></div>
      </div>
      <div className={`font-display font-semibold ${sevText(sev)}`}>{delta}</div>
    </li>
  );
}
function sevBgBorder(s: RiskStatus) {
  return s === "high" ? "bg-[color:var(--risk-high)]/10 border-[color:var(--risk-high)]/30"
    : s === "elevated" ? "bg-[color:var(--risk-elevated)]/10 border-[color:var(--risk-elevated)]/30"
    : s === "medium" ? "bg-[color:var(--risk-medium)]/10 border-[color:var(--risk-medium)]/30"
    : "bg-[color:var(--risk-low)]/10 border-[color:var(--risk-low)]/30";
}

function Sparkline({ values, className }: { values: number[]; className?: string }) {
  const w = 320, h = 110, pad = 8;
  const max = Math.max(...values), min = Math.min(...values);
  const dx = (w - pad * 2) / (values.length - 1);
  const sy = (v: number) => h - pad - ((v - min) / (max - min || 1)) * (h - pad * 2);
  const points = values.map((v, i) => `${pad + i * dx},${sy(v)}`).join(" ");
  const area = `M${pad},${h} L${points.split(" ").join(" L")} L${w - pad},${h} Z`;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} className={className} preserveAspectRatio="none">
      <defs>
        <linearGradient id="spkA" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stopColor="oklch(0.92 0.22 128)" stopOpacity="0.35" />
          <stop offset="100%" stopColor="oklch(0.92 0.22 128)" stopOpacity="0" />
        </linearGradient>
      </defs>
      <path d={area} fill="url(#spkA)" />
      <polyline points={points} fill="none" stroke="oklch(0.92 0.22 128)" strokeWidth="1.8" />
      <circle cx={pad + (values.length - 1) * dx} cy={sy(values[values.length - 1])} r="3.5" fill="oklch(0.92 0.22 128)" />
    </svg>
  );
}

function DriftGauge({ value }: { value: number }) {
  const segments = 32;
  const filled = Math.round((value / 100) * segments);
  return (
    <div className="relative w-full h-36 flex items-end justify-center">
      <svg viewBox="0 0 200 110" className="w-full h-full">
        {Array.from({ length: segments }).map((_, i) => {
          const a = Math.PI - (i / (segments - 1)) * Math.PI;
          const x1 = 100 + Math.cos(a) * 70;
          const y1 = 100 - Math.sin(a) * 70;
          const x2 = 100 + Math.cos(a) * 88;
          const y2 = 100 - Math.sin(a) * 88;
          return (
            <line key={i} x1={x1} y1={y1} x2={x2} y2={y2}
              stroke={i < filled ? "oklch(0.92 0.22 128)" : "oklch(1 0 0 / 0.1)"}
              strokeWidth="4" strokeLinecap="round" />
          );
        })}
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-end pb-2">
        <div className="font-display text-3xl font-semibold">{value}%</div>
        <div className="text-[11px] text-muted-foreground">Total Drift</div>
      </div>
    </div>
  );
}

function VerificationDonut({ completed, total }: { completed: number; total: number }) {
  const pct = completed / total;
  const r = 38, c = 2 * Math.PI * r;
  return (
    <div className="relative h-28 w-28 shrink-0">
      <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
        <circle cx="50" cy="50" r={r} stroke="oklch(1 0 0 / 0.1)" strokeWidth="6" fill="none" />
        <circle cx="50" cy="50" r={r} stroke="oklch(0.92 0.22 128)" strokeWidth="6" fill="none"
          strokeLinecap="round"
          strokeDasharray={`${c * pct} ${c}`}
          style={{ filter: "drop-shadow(0 0 6px oklch(0.92 0.22 128 / 0.55))" }} />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <div className="font-display text-xl font-semibold">{completed}<span className="text-muted-foreground text-sm">/{total}</span></div>
        <div className="text-[10px] text-muted-foreground">Completed</div>
      </div>
    </div>
  );
}

/* ---------------- Engine Analysis ---------------- */
function EngineAnalysis({ trace }: { trace: AIReasoningTrace }) {
  const [tab, setTab] = useState<"loopA" | "graphrag" | "timegpt" | "survival" | "router" | "guardrails">("loopA");
  const tabs = [
    { id: "loopA", l: "Loop A Drift Gate" },
    { id: "graphrag", l: "GraphRAG" },
    { id: "timegpt", l: "TimeGPT" },
    { id: "survival", l: "Survival" },
    { id: "router", l: "Router" },
    { id: "guardrails", l: "Guardrails" },
  ] as const;

  return (
    <section className="rounded-2xl border border-border bg-card glass p-5">
      <header className="flex items-center justify-between mb-4 flex-wrap gap-2">
        <div>
          <h3 className="text-sm font-semibold">Engine Analysis</h3>
          <p className="text-[11px] text-muted-foreground">Which HYDRA component produced which signal.</p>
        </div>
        <span className="text-[11px] text-muted-foreground font-mono">trace_id: {trace.trace_id}</span>
      </header>

      <div className="flex flex-wrap gap-1.5 mb-4 border-b border-border pb-3">
        {tabs.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`rounded-md px-3 py-1.5 text-xs ${
              tab === t.id ? "bg-neon-soft text-neon" : "border border-border text-muted-foreground hover:text-foreground"
            }`}
          >
            {t.l}
          </button>
        ))}
      </div>

      <div className="text-sm">
        {tab === "loopA" && (
          <Grid>
            <Kv k="VAE reconstruction error" v={trace.loop_a.vae_reconstruction_error} />
            <Kv k="Drift threshold" v={trace.loop_a.drift_threshold} />
            <Kv k="Drift detected" v={trace.loop_a.drift_detected ? "Yes" : "No"} highlight={trace.loop_a.drift_detected} />
            <Kv k="Embedding shift score" v={trace.loop_a.embedding_shift_score} />
            <Kv k="Decision" v={trace.loop_a.decision} />
            <Kv k="Cost" v={`$${trace.loop_a.cost_usd.toFixed(4)}`} />
            <div className="col-span-full">
              <div className="text-[11px] text-muted-foreground mb-1">Top keywords</div>
              <div className="flex flex-wrap gap-1.5">
                {trace.loop_a.top_keywords.map((k) => (
                  <span key={k} className="rounded-md bg-[color:var(--risk-high)]/15 text-[color:var(--risk-high)] text-xs px-2 py-0.5 border border-[color:var(--risk-high)]/30">
                    {k}
                  </span>
                ))}
              </div>
            </div>
          </Grid>
        )}
        {tab === "graphrag" && (
          <Grid>
            <Kv k="New entity" v={trace.loop_b.graphrag.new_entity} />
            <Kv k="Triple status" v={trace.loop_b.graphrag.triple_status} />
            <Kv k="Timestamp slice" v={trace.loop_b.graphrag.timestamp_slice} />
          </Grid>
        )}
        {tab === "timegpt" && (
          <Grid>
            <Kv k="Forecast horizon" v={`${trace.loop_b.timegpt.horizon_days} days`} />
            <Kv k="Anomaly score" v={trace.loop_b.timegpt.anomaly_score} highlight />
            <Kv k="Uncertainty interval" v={`${trace.loop_b.timegpt.uncertainty[0]} – ${trace.loop_b.timegpt.uncertainty[1]}`} />
            <div className="col-span-full text-foreground/90">{trace.loop_b.timegpt.summary}</div>
          </Grid>
        )}
        {tab === "survival" && (
          <Grid>
            <Kv k="Model" v={trace.loop_b.survival.model} />
            <Kv k="Time-to-decay" v={`${trace.loop_b.survival.time_to_decay_days} days`} highlight />
            <Kv k="Confidence" v={`${Math.round(trace.loop_b.survival.confidence * 100)}%`} />
            <div className="col-span-full text-foreground/90">{trace.loop_b.survival.summary}</div>
          </Grid>
        )}
        {tab === "router" && (
          <Grid>
            <Kv k="Path" v={trace.loop_b.router.path.toUpperCase()} highlight />
            <Kv k="Reason" v={trace.loop_b.router.reason} />
            <Kv k="Model" v={trace.loop_b.router.model} />
            <Kv k="Tokens" v={trace.loop_b.router.tokens} />
            <Kv k="Cost" v={`$${trace.loop_b.router.cost_usd}`} />
          </Grid>
        )}
        {tab === "guardrails" && (
          <ul className="grid grid-cols-1 sm:grid-cols-2 gap-2">
            {trace.guardrail_checks.map((g) => (
              <li key={g} className="flex items-center gap-2 rounded-md border border-border bg-surface-2/60 px-3 py-2 text-sm">
                <span className="text-neon">✓</span> {g}
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="mt-5 rounded-xl border border-neon/30 bg-neon-soft/60 p-4">
        <div className="text-[11px] uppercase tracking-wider text-neon mb-1">Decision Rationale</div>
        <p className="text-sm text-foreground/90">{trace.decision_rationale}</p>
        <div className="mt-3 text-[11px] text-muted-foreground">
          Audit citations: {trace.audit_citations.join(" · ")}
        </div>
      </div>
    </section>
  );
}

function Grid({ children }: { children: React.ReactNode }) {
  return <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">{children}</div>;
}
function Kv({ k, v, highlight }: { k: string; v: React.ReactNode; highlight?: boolean }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2/50 p-3">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</div>
      <div className={`mt-1 font-mono text-sm ${highlight ? "text-neon" : "text-foreground/90"}`}>{String(v)}</div>
    </div>
  );
}

function KYCDriftCard({ record }: { record: KYCDriftRecord }) {
  return (
    <section className="rounded-2xl border border-border bg-card glass p-5">
      <header className="flex items-center justify-between mb-3">
        <h3 className="text-sm font-semibold">KYC Drift Diff</h3>
        <RiskBadge level={record.overall_drift_severity} />
      </header>
      <div className="overflow-x-auto rounded-lg border border-border">
        <table className="w-full text-sm">
          <thead className="bg-surface-2/60 text-[11px] uppercase tracking-wider text-muted-foreground">
            <tr>
              <Th>Field</Th><Th>Baseline</Th><Th>Current</Th><Th>Drift</Th><Th>Source</Th>
            </tr>
          </thead>
          <tbody>
            {record.drifted_fields.map((f) => (
              <tr key={f.field} className="border-t border-border">
                <Td><span className="font-mono text-xs text-foreground/90">{f.field}</span></Td>
                <Td className="text-muted-foreground">{f.baseline_value}</Td>
                <Td>{f.current_value}</Td>
                <Td><RiskBadge level={f.drift_severity} /></Td>
                <Td className="text-neon">{f.source}</Td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <p className="mt-3 text-sm text-[color:var(--risk-elevated)] flex items-center gap-2">
        <AlertTriangle size={14} /> {record.summary}
      </p>
    </section>
  );
}
function Th({ children }: { children: React.ReactNode }) { return <th className="text-left px-3 py-2 font-medium">{children}</th>; }
function Td({ children, className = "" }: { children: React.ReactNode; className?: string }) { return <td className={`px-3 py-2.5 align-middle ${className}`}>{children}</td>; }
