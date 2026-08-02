import { createFileRoute, Link, useNavigate } from "@tanstack/react-router";
import { useEffect, useMemo, useState } from "react";
import {
  ArrowLeft,
  AlertTriangle,
  Building2,
  Clock,
  Cpu,
  ExternalLink,
  ShieldAlert,
  UserPlus,
  XCircle,
  Loader2,
  Network,
  FileSearch,
  GitBranch,
  Sparkles,
} from "lucide-react";
import { toast } from "sonner";
import { AppLayout } from "@/components/layout/AppLayout";
import { RiskBadge } from "@/components/ui/risk-badge";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { getAlertById, getKYCDriftRecord } from "@/lib/services";
import type {
  AIReasoningTrace,
  Alert,
  GovernanceRecord,
  KYCDriftRecord,
  RiskStatus,
} from "@/lib/types";

export const Route = createFileRoute("/alerts/$id")({
  head: ({ params }) => ({ meta: [{ title: `Investigation ${params.id} — HYDRA` }] }),
  component: InvestigationPage,
});

type CaseStatus = "open" | "investigating" | "escalated" | "rekyc_requested" | "dismissed";

const analysts = [
  "Anna Rivera",
  "Marcus Chen",
  "Priya Shah",
  "Diego Fernandez",
  "Lena Kowalski",
];

function InvestigationPage() {
  const { id } = Route.useParams();
  const navigate = useNavigate();

  const [alert, setAlert] = useState<Alert | null>(null);
  const [trace, setTrace] = useState<AIReasoningTrace | null>(null);
  const [drift, setDrift] = useState<KYCDriftRecord | null>(null);
  const [gov, setGov] = useState<GovernanceRecord | null>(null);
  const [loading, setLoading] = useState(true);

  // Case action state
  const [status, setStatus] = useState<CaseStatus>("open");
  const [assignee, setAssignee] = useState<string | null>(null);
  const [pending, setPending] = useState<null | "escalate" | "rekyc">(null);
  const [dismissOpen, setDismissOpen] = useState(false);
  const [assignOpen, setAssignOpen] = useState(false);
  const [dismissReason, setDismissReason] = useState("");

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    (async () => {
      const a = await getAlertById(id);
      if (cancelled) return;
      if (!a) {
        setLoading(false);
        return;
      }
      setAlert(a);
      setStatus((a.status as CaseStatus) ?? "open");
      // Trace and governance are embedded directly on the backend alert
      // response; only KYC drift lives behind its own endpoint.
      const d = await getKYCDriftRecord(a.customerId);
      if (cancelled) return;
      setTrace(a.reasoningTrace ?? null);
      setGov(a.governance ?? null);
      setDrift(d ?? null);
      setLoading(false);
    })();
    return () => {
      cancelled = true;
    };
  }, [id]);

  const summary = useMemo(() => {
    if (!alert) return "";
    const tg = trace?.loop_b?.timegpt?.summary;
    const sv = trace?.loop_b?.survival?.summary;
    return [
      `${alert.driftType} detected for ${alert.customerName}.`,
      tg ? `TimeGPT: ${tg}.` : null,
      sv ? `Survival model: ${sv}.` : null,
      trace?.loop_b?.router.path === "heavy"
        ? "Routed to heavy reasoning path for escalation."
        : null,
    ]
      .filter(Boolean)
      .join(" ");
  }, [alert, trace]);

  const sourceLabel = useMemo(() => {
    if (!alert?.citations?.length) return "—";
    const sources = new Set(
      alert.citations.map((c) => c.provider ?? c.source).filter(Boolean) as string[],
    );
    return sources.size ? Array.from(sources).join(" / ") : "—";
  }, [alert]);

  if (loading && !alert) {
    return (
      <AppLayout>
        <div className="px-6 lg:px-10 py-16 flex items-center gap-3 text-muted-foreground">
          <Loader2 className="animate-spin" size={18} />
          Loading case…
        </div>
      </AppLayout>
    );
  }
  if (!alert)
    return (
      <AppLayout>
        <div className="px-6 lg:px-10 py-16">
          <button
            onClick={() => navigate({ to: "/alerts" })}
            className="text-xs uppercase tracking-[0.2em] text-muted-foreground hover:text-neon mb-4 inline-flex items-center gap-1.5"
          >
            <ArrowLeft size={14} /> Back to alerts
          </button>
          <h1 className="text-2xl font-display font-semibold">Alert not found</h1>
          <p className="text-sm text-muted-foreground mt-1">
            Alert <span className="font-mono">{id}</span> doesn't exist.
          </p>
        </div>
      </AppLayout>
    );

  function handleEscalate() {
    setPending("escalate");
    setTimeout(() => {
      setStatus("escalated");
      setPending(null);
      toast.success("Case escalated to senior risk officer", {
        description: `Case ${alert!.id} routed to escalation queue.`,
      });
    }, 600);
  }
  function handleRekyc() {
    setPending("rekyc");
    setTimeout(() => {
      setStatus("rekyc_requested");
      setPending(null);
      toast.success("Re-KYC request submitted", {
        description: `Customer ${alert!.customerName} notified.`,
      });
    }, 600);
  }
  function handleDismissSubmit() {
    if (!dismissReason.trim()) {
      toast.error("Please provide a reason");
      return;
    }
    setStatus("dismissed");
    setDismissOpen(false);
    toast("Case dismissed", { description: dismissReason.trim() });
    setDismissReason("");
  }
  function handleAssign(name: string) {
    setAssignee(name);
    setAssignOpen(false);
    setStatus((s) => (s === "open" ? "investigating" : s));
    toast.success(`Assigned to ${name}`);
  }

  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1400px]">
        <button
          onClick={() => navigate({ to: "/alerts" })}
          className="inline-flex items-center gap-1.5 text-xs uppercase tracking-[0.2em] text-muted-foreground hover:text-neon transition-colors mb-4 cursor-pointer"
        >
          <ArrowLeft size={14} /> Back to alerts
        </button>

        {/* Header */}
        <div className="rounded-2xl border border-border bg-card glass p-6 mb-6">
          <div className="flex items-start justify-between gap-4 flex-wrap">
            <div className="min-w-0">
              <div className="flex items-center gap-2 flex-wrap mb-2">
                <span className="text-[11px] font-mono text-muted-foreground uppercase tracking-wider">
                  Case {alert.id}
                </span>
                <CaseStatusBadge status={status} />
                <RiskBadge level={alert.severity as RiskStatus} />
                <span className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-[11px] font-mono">
                  {alert.driftType}
                </span>
              </div>
              <h1 className="text-2xl lg:text-3xl font-display font-semibold flex items-center gap-3">
                <AlertTriangle
                  size={22}
                  className={
                    alert.severity === "high"
                      ? "text-[color:var(--risk-high)]"
                      : alert.severity === "elevated"
                        ? "text-[color:var(--risk-elevated)]"
                        : "text-[color:var(--risk-medium)]"
                  }
                />
                {alert.title}
              </h1>
              <div className="mt-2 flex items-center gap-4 text-sm text-muted-foreground flex-wrap">
                <Link
                  to="/customers/$id"
                  params={{ id: alert.customerId }}
                  className="inline-flex items-center gap-1.5 text-neon hover:underline"
                >
                  <Building2 size={14} /> {alert.customerName}
                </Link>
                <span className="inline-flex items-center gap-1.5">
                  <Clock size={14} /> {alert.timestamp}
                </span>
                {assignee && (
                  <span className="inline-flex items-center gap-1.5">
                    <UserPlus size={14} /> Assigned to{" "}
                    <span className="text-foreground">{assignee}</span>
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Summary */}
          <div className="mt-5 rounded-xl border border-neon/25 bg-neon-soft/30 p-4">
            <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-neon mb-1.5">
              <Sparkles size={12} /> Case summary
            </div>
            <p className="text-sm text-foreground/90 leading-relaxed">{summary}</p>
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
          <div className="lg:col-span-2 space-y-5">
            {/* A. Raw Signal */}
            <Section title="Raw Signal" icon={<FileSearch size={14} />}>
              <div className="grid grid-cols-2 gap-3 text-sm">
                <KV k="Entity" v={alert.customerName} />
                <KV k="Signal type" v={alert.driftType} />
                <KV k="Source" v={sourceLabel} />
                <KV k="Timestamp" v={alert.timestamp} />
              </div>
              <p className="mt-4 text-sm text-foreground/90 border-t border-border pt-3">
                {alert.explanation}
              </p>
              {!!alert.matchedRiskTerms?.length && (
                <div className="mt-4 border-t border-border pt-3">
                  <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1.5">
                    Matched risk terms
                  </div>
                  <div className="flex flex-wrap gap-1.5">
                    {alert.matchedRiskTerms.map((term) => (
                      <span
                        key={term}
                        className="rounded-md border border-border bg-surface-2 px-2 py-0.5 text-xs font-mono"
                      >
                        {term}
                      </span>
                    ))}
                  </div>
                </div>
              )}
            </Section>

            {/* B. AI Reasoning Trace */}
            {trace && (
              <Section title="AI Reasoning Trace" icon={<Cpu size={14} />} accent>
                <div>
                  <div className="text-[11px] uppercase tracking-wider text-neon mb-1.5">
                    Decision rationale
                  </div>
                  <p className="text-sm text-foreground/90 leading-relaxed">
                    {trace.decision_rationale}
                  </p>
                </div>
                <div className="mt-4 grid grid-cols-2 md:grid-cols-4 gap-2">
                  <Stat label="Router path" v={trace.loop_b?.router.path ?? "—"} />
                  <Stat label="Model" v={trace.loop_b?.router.model ?? "—"} />
                  <Stat label="Tokens" v={String(trace.total_tokens_used)} />
                  <Stat label="Cost" v={`$${trace.total_cost_usd}`} />
                </div>
                {trace.loop_b ? (
                  <div className="mt-4 grid grid-cols-1 md:grid-cols-2 gap-3">
                    <SubCard title="Forecast (TimeGPT)">
                      {trace.loop_b.timegpt.summary} · anomaly score{" "}
                      {trace.loop_b.timegpt.anomaly_score}
                    </SubCard>
                    <SubCard title="Survival model">
                      {trace.loop_b.survival.summary} · confidence{" "}
                      {trace.loop_b.survival.confidence}
                    </SubCard>
                  </div>
                ) : (
                  <p className="mt-4 text-xs text-muted-foreground">
                    Layer 2 forecasting was not run for this alert.
                  </p>
                )}
              </Section>
            )}

            {/* C. KYC Drift Fields */}
            {drift && (
              <Section title="KYC Drift Fields" icon={<GitBranch size={14} />}>
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-[11px] uppercase tracking-wider text-muted-foreground border-b border-border">
                        <th className="text-left font-medium py-2 pr-3">Field</th>
                        <th className="text-left font-medium py-2 pr-3">Baseline</th>
                        <th className="text-left font-medium py-2 pr-3">Current</th>
                        <th className="text-left font-medium py-2 pr-3">Severity</th>
                        <th className="text-left font-medium py-2">Source</th>
                      </tr>
                    </thead>
                    <tbody>
                      {drift.drifted_fields.map((f) => (
                        <tr key={f.field} className="border-b border-border/60 last:border-0">
                          <td className="py-2.5 pr-3 font-mono text-xs">{f.field}</td>
                          <td className="py-2.5 pr-3 text-muted-foreground">{f.baseline_value}</td>
                          <td className="py-2.5 pr-3">{f.current_value}</td>
                          <td className="py-2.5 pr-3">
                            <RiskBadge level={f.drift_severity} />
                          </td>
                          <td className="py-2.5 text-xs text-muted-foreground">{f.source}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Section>
            )}

            {/* D. Citations */}
            {!!alert.citations?.length && (
              <Section title="Citations" icon={<Network size={14} />}>
                <ul className="space-y-2">
                  {alert.citations.map((c, i) => (
                    <li
                      key={`${c.url ?? c.title}-${i}`}
                      className="rounded-lg border border-border bg-surface-2/60 px-3 py-2.5 hover:border-neon/40 hover:bg-surface-2 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-3">
                        <div className="min-w-0">
                          <div className="text-sm font-medium truncate">
                            {c.title ?? "Untitled source"}
                          </div>
                          <div className="text-xs text-muted-foreground font-mono truncate">
                            {c.provider ?? c.source ?? "unknown source"}
                            {c.query ? ` · query: "${c.query}"` : ""}
                          </div>
                        </div>
                        {c.url && (
                          <a
                            href={c.url}
                            target="_blank"
                            rel="noreferrer"
                            className="shrink-0 inline-flex items-center gap-1 text-[11px] text-neon hover:underline"
                          >
                            open <ExternalLink size={11} />
                          </a>
                        )}
                      </div>
                      {c.reason && (
                        <p className="mt-1.5 text-xs text-foreground/80 border-t border-border/60 pt-1.5">
                          {c.reason}
                        </p>
                      )}
                    </li>
                  ))}
                </ul>
              </Section>
            )}
          </div>

          {/* Right column */}
          <div className="space-y-5">
            {/* E. Governance / Workflow */}
            <Section title="Governance & Workflow" icon={<ShieldAlert size={14} />}>
              <Timeline status={status} gov={gov} assignee={assignee} />
              {gov?.requires_manual_approval && (
                <div className="mt-4 rounded-lg border border-[color:var(--risk-elevated)]/30 bg-[color:var(--risk-elevated)]/10 px-3 py-2 text-xs">
                  Manual approval required by{" "}
                  <span className="font-mono">{gov.approval_deadline}</span>
                </div>
              )}
            </Section>

            {/* F. Recommended Action */}
            <Section title="Recommended Action" icon={<Sparkles size={14} />}>
              <p className="text-sm text-foreground/90 mb-4">
                {alert.recommendedAction ?? (
                  <>
                    Escalate to senior compliance and request re-KYC due to{" "}
                    <span className="text-foreground font-medium">
                      {drift?.drifted_fields[0]?.field ?? "drift"}
                    </span>{" "}
                    change.
                  </>
                )}
              </p>
              <div className="grid grid-cols-1 gap-2">
                <Button
                  onClick={handleEscalate}
                  disabled={pending === "escalate" || status === "escalated"}
                  className="bg-[color:var(--risk-high)] text-white hover:bg-[color:var(--risk-high)]/90 hover:shadow-[0_0_18px_-4px_oklch(0.55_0.24_25/0.6)] transition-all"
                >
                  {pending === "escalate" && <Loader2 className="animate-spin" />}
                  {status === "escalated" ? "Escalated" : "Escalate case"}
                </Button>
                <Button
                  onClick={handleRekyc}
                  disabled={pending === "rekyc" || status === "rekyc_requested"}
                  className="bg-neon text-primary-foreground hover:bg-neon/90 hover:shadow-[0_0_18px_-4px_oklch(0.92_0.22_128/0.6)] transition-all"
                >
                  {pending === "rekyc" && <Loader2 className="animate-spin" />}
                  {status === "rekyc_requested" ? "Re-KYC requested" : "Request Re-KYC"}
                </Button>
                <Button
                  variant="outline"
                  onClick={() => setAssignOpen(true)}
                  className="hover:border-neon/40 hover:text-neon transition-colors"
                >
                  <UserPlus /> {assignee ? "Reassign analyst" : "Assign analyst"}
                </Button>
                <Button
                  variant="ghost"
                  onClick={() => setDismissOpen(true)}
                  disabled={status === "dismissed"}
                  className="text-muted-foreground hover:text-[color:var(--risk-high)] hover:bg-[color:var(--risk-high)]/10 transition-colors"
                >
                  <XCircle /> {status === "dismissed" ? "Dismissed" : "Dismiss with reason"}
                </Button>
              </div>
            </Section>
          </div>
        </div>
      </div>

      {/* Dismiss modal */}
      <Dialog open={dismissOpen} onOpenChange={setDismissOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Dismiss case</DialogTitle>
            <DialogDescription>
              Provide a short justification. This will be appended to the audit log.
            </DialogDescription>
          </DialogHeader>
          <Textarea
            placeholder="e.g. False positive — counterparty re-verified manually."
            value={dismissReason}
            onChange={(e) => setDismissReason(e.target.value)}
            rows={4}
          />
          <DialogFooter>
            <Button variant="ghost" onClick={() => setDismissOpen(false)}>
              Cancel
            </Button>
            <Button
              onClick={handleDismissSubmit}
              className="bg-[color:var(--risk-high)] text-white hover:bg-[color:var(--risk-high)]/90"
            >
              Confirm dismissal
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* Assign modal */}
      <Dialog open={assignOpen} onOpenChange={setAssignOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Assign analyst</DialogTitle>
            <DialogDescription>Select an analyst to own this case.</DialogDescription>
          </DialogHeader>
          <div className="grid gap-1.5">
            {analysts.map((name) => (
              <button
                key={name}
                onClick={() => handleAssign(name)}
                className={`flex items-center gap-3 rounded-lg border px-3 py-2.5 text-left text-sm transition-all cursor-pointer ${
                  assignee === name
                    ? "border-neon/60 bg-neon-soft text-neon"
                    : "border-border bg-surface-2/60 hover:border-neon/40 hover:bg-surface-2"
                }`}
              >
                <span className="h-7 w-7 rounded-full bg-neon/20 grid place-items-center text-neon text-xs font-semibold">
                  {name
                    .split(" ")
                    .map((p) => p[0])
                    .join("")}
                </span>
                {name}
              </button>
            ))}
          </div>
        </DialogContent>
      </Dialog>
    </AppLayout>
  );
}

function Section({
  title,
  icon,
  accent,
  children,
}: {
  title: string;
  icon?: React.ReactNode;
  accent?: boolean;
  children: React.ReactNode;
}) {
  return (
    <section
      className={`rounded-2xl border p-5 transition-colors ${
        accent
          ? "border-neon/30 bg-neon-soft/20"
          : "border-border bg-card glass hover:border-border/80"
      }`}
    >
      <div
        className={`flex items-center gap-1.5 text-[11px] uppercase tracking-wider mb-3 ${
          accent ? "text-neon" : "text-muted-foreground"
        }`}
      >
        {icon}
        {title}
      </div>
      {children}
    </section>
  );
}

function KV({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div>
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground">{k}</div>
      <div className="text-foreground/90">{v}</div>
    </div>
  );
}
function Stat({ label, v }: { label: string; v: string }) {
  return (
    <div className="rounded-md bg-surface-2/70 px-2.5 py-2 border border-border/60">
      <div className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</div>
      <div className="font-mono text-xs mt-0.5">{v}</div>
    </div>
  );
}
function SubCard({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-border bg-surface-2/40 px-3 py-2.5">
      <div className="text-[11px] uppercase tracking-wider text-muted-foreground mb-1">{title}</div>
      <div className="text-sm text-foreground/90">{children}</div>
    </div>
  );
}

function CaseStatusBadge({ status }: { status: CaseStatus }) {
  const map: Record<CaseStatus, { label: string; cls: string }> = {
    open: { label: "Open", cls: "bg-surface-2 text-muted-foreground border-border" },
    investigating: {
      label: "Investigating",
      cls: "bg-[color:var(--risk-medium)]/15 text-[color:var(--risk-medium)] border-[color:var(--risk-medium)]/30",
    },
    escalated: {
      label: "Escalated",
      cls: "bg-[color:var(--risk-high)]/15 text-[color:var(--risk-high)] border-[color:var(--risk-high)]/30",
    },
    rekyc_requested: {
      label: "Re-KYC requested",
      cls: "bg-neon-soft text-neon border-neon/30",
    },
    dismissed: {
      label: "Dismissed",
      cls: "bg-surface-2 text-muted-foreground border-border line-through",
    },
  };
  const s = map[status];
  return (
    <span className={`rounded-md border px-2 py-0.5 text-[11px] font-semibold ${s.cls}`}>
      {s.label}
    </span>
  );
}

function Timeline({
  status,
  gov,
  assignee,
}: {
  status: CaseStatus;
  gov: GovernanceRecord | null;
  assignee: string | null;
}) {
  const steps: { label: string; done: boolean; note?: string }[] = [
    { label: "Initial AI flag", done: true, note: "Loop A drift gate passed" },
    { label: "Graph + reasoning trace", done: true, note: "GraphRAG · TimeGPT · Survival" },
    {
      label: "Assigned to analyst",
      done: Boolean(assignee),
      note: assignee ?? "Awaiting assignment",
    },
    {
      label: "Compliance review",
      done: status === "investigating" || status === "escalated" || status === "rekyc_requested",
    },
    {
      label: "Escalation / Re-KYC",
      done: status === "escalated" || status === "rekyc_requested",
      note:
        status === "escalated"
          ? "Senior risk officer"
          : status === "rekyc_requested"
            ? "Customer notified"
            : gov?.requires_manual_approval
              ? `Deadline ${gov.approval_deadline}`
              : undefined,
    },
    {
      label: "Final decision",
      done: status === "dismissed",
      note: status === "dismissed" ? "Dismissed by analyst" : "Pending",
    },
  ];
  return (
    <ol className="relative space-y-3 pl-5">
      <span className="absolute left-[7px] top-1 bottom-1 w-px bg-border" />
      {steps.map((s, i) => (
        <li key={i} className="relative">
          <span
            className={`absolute -left-5 top-1 h-2 w-2 rounded-full border-2 ${
              s.done
                ? "bg-neon border-neon shadow-[0_0_8px_oklch(0.92_0.22_128/0.6)]"
                : "bg-background border-border"
            }`}
          />
          <div className="text-sm">{s.label}</div>
          {s.note && <div className="text-[11px] text-muted-foreground">{s.note}</div>}
        </li>
      ))}
    </ol>
  );
}
