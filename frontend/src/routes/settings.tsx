import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { Moon, Sun, RotateCcw } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { useTheme } from "@/components/theme-provider";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { Button } from "@/components/ui/button";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";

export const Route = createFileRoute("/settings")({
  head: () => ({ meta: [{ title: "Settings — HYDRA" }] }),
  component: SettingsPage,
});

/* ---------- localStorage helper ---------- */
function usePersistedState<T>(key: string, initial: T): [T, (v: T | ((p: T) => T)) => void] {
  const [v, setV] = useState<T>(() => {
    if (typeof window === "undefined") return initial;
    try {
      const raw = window.localStorage.getItem(key);
      return raw ? (JSON.parse(raw) as T) : initial;
    } catch {
      return initial;
    }
  });
  useEffect(() => {
    try {
      window.localStorage.setItem(key, JSON.stringify(v));
    } catch {}
  }, [key, v]);
  return [v, setV];
}

function SettingsPage() {
  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1100px]">
        <header className="mb-6">
          <div className="text-xs uppercase tracking-[0.2em] text-muted-foreground mb-1">Configuration</div>
          <h1 className="text-3xl font-display font-semibold">Settings</h1>
        </header>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-5">
          <Section title="Analyst Profile">
            <AnalystProfileCard />
          </Section>

          <Section title="Backend Mode">
            <BackendModeCard />
          </Section>

          <Section title="Theme">
            <ThemeToggleCard />
          </Section>

          <Section title="Notifications">
            <NotificationsCard />
          </Section>

          <Section title="Risk Thresholds">
            <RiskThresholdsCard />
          </Section>
        </div>
      </div>
    </AppLayout>
  );
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-border bg-card glass p-5 lime-outline">
      <h3 className="font-display font-semibold mb-4">{title}</h3>
      <div className="space-y-3">{children}</div>
    </div>
  );
}

function Row({ k, v }: { k: string; v: React.ReactNode }) {
  return (
    <div className="flex items-center justify-between text-sm">
      <span className="text-muted-foreground">{k}</span>
      <span>{v}</span>
    </div>
  );
}

/* ---------- Analyst Profile ---------- */
function AnalystProfileCard() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Row k="Name" v="Anna Rivera" />
      <Row k="Role" v="Compliance Analyst" />
      <Row k="Email" v="anna.rivera@hydra.bank" />
      <Row k="Team" v="EU Corporate AML" />
      <div className="pt-2">
        <Button size="sm" variant="outline" onClick={() => setOpen(true)}>
          Edit profile
        </Button>
      </div>
      <Dialog open={open} onOpenChange={setOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Edit profile</DialogTitle>
            <DialogDescription>
              Profile editing is disabled in demo mode. In production, analyst identity is provisioned via SSO and managed by your IAM administrator.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button onClick={() => setOpen(false)}>Got it</Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </>
  );
}

/* ---------- Backend Mode ---------- */
function BackendModeCard() {
  const [mode, setMode] = usePersistedState<"mock" | "live">("hydra-backend-mode", "mock");
  const isMock = mode === "mock";
  return (
    <>
      <p className="text-xs text-muted-foreground mb-1">
        HYDRA frontend currently consumes mock data. Switch to live API once endpoints are deployed.
      </p>
      <div className="inline-flex rounded-lg border border-border overflow-hidden">
        <button
          type="button"
          onClick={() => setMode("mock")}
          className={`px-3 py-1.5 text-sm border-r border-border transition-colors ${
            isMock ? "bg-neon-soft text-neon" : "bg-surface-2 text-muted-foreground hover:text-foreground"
          }`}
        >
          Mock data
        </button>
        <button
          type="button"
          onClick={() => setMode("live")}
          className={`px-3 py-1.5 text-sm transition-colors ${
            !isMock ? "bg-neon-soft text-neon" : "bg-surface-2 text-muted-foreground hover:text-foreground"
          }`}
        >
          Live API
        </button>
      </div>
      <div className="mt-3 text-[11px] text-muted-foreground">
        API status:{" "}
        {isMock ? (
          <span className="text-neon">● mock data active</span>
        ) : (
          <span className="text-[color:var(--risk-elevated)]">● waiting for backend connection</span>
        )}
      </div>
      {!isMock && (
        <div className="mt-2 rounded-md border border-[color:var(--risk-elevated)]/30 bg-[color:var(--risk-elevated)]/10 px-3 py-2 text-[11px] text-[color:var(--risk-elevated)]">
          Live API mode is prepared, but backend endpoints are not connected yet.
        </div>
      )}
    </>
  );
}

/* ---------- Theme ---------- */
function ThemeToggleCard() {
  const { theme, setTheme } = useTheme();
  const isDark = theme === "dark";
  return (
    <div className="space-y-4">
      <Row k="Current mode" v={<span className="text-neon capitalize">{theme}</span>} />
      <Row k="Accent" v="Neon Lime" />
      <div className="pt-1">
        <div className="text-xs text-muted-foreground mb-2">Switch theme</div>
        <div className="inline-flex rounded-lg border border-border overflow-hidden">
          <button
            type="button"
            onClick={() => setTheme("dark")}
            aria-pressed={isDark}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm transition-colors border-r border-border ${
              isDark ? "bg-neon-soft text-neon" : "bg-surface-2 text-muted-foreground hover:text-foreground"
            }`}
          >
            <Moon size={14} /> Dark Mode
          </button>
          <button
            type="button"
            onClick={() => setTheme("light")}
            aria-pressed={!isDark}
            className={`flex items-center gap-2 px-3 py-1.5 text-sm transition-colors ${
              !isDark ? "bg-neon-soft text-neon" : "bg-surface-2 text-muted-foreground hover:text-foreground"
            }`}
          >
            <Sun size={14} /> Light Mode
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---------- Notifications ---------- */
type Notifs = { email: boolean; slack: boolean; sounds: boolean };
function NotificationsCard() {
  const [n, setN] = usePersistedState<Notifs>("hydra-notifications", {
    email: true,
    slack: true,
    sounds: false,
  });
  const toggle = (k: keyof Notifs) => setN((p) => ({ ...p, [k]: !p[k] }));
  return (
    <>
      <ToggleRow label="Email digests (daily)" checked={n.email} onChange={() => toggle("email")} />
      <ToggleRow label="Slack alerts on HIGH severity" checked={n.slack} onChange={() => toggle("slack")} />
      <ToggleRow label="In-app sounds" checked={n.sounds} onChange={() => toggle("sounds")} />
    </>
  );
}

function ToggleRow({ label, checked, onChange }: { label: string; checked: boolean; onChange: () => void }) {
  return (
    <label className="flex items-center justify-between text-sm cursor-pointer">
      <span>{label}</span>
      <Switch checked={checked} onCheckedChange={onChange} />
    </label>
  );
}

/* ---------- Risk Thresholds ---------- */
type Thresholds = { drift: number; routerT: number; survival: number };
const THRESH_DEFAULTS: Thresholds = { drift: 0.41, routerT: 7, survival: 3 };

function RiskThresholdsCard() {
  const [t, setT] = usePersistedState<Thresholds>("hydra-thresholds", THRESH_DEFAULTS);
  return (
    <>
      <SliderRow
        label="Drift gate threshold"
        value={t.drift}
        min={0}
        max={1}
        step={0.01}
        display={t.drift.toFixed(2)}
        onChange={(v) => setT((p) => ({ ...p, drift: v }))}
      />
      <SliderRow
        label="Heavy-router T cutoff (days)"
        value={t.routerT}
        min={1}
        max={14}
        step={1}
        display={`${t.routerT}d`}
        onChange={(v) => setT((p) => ({ ...p, routerT: v }))}
      />
      <SliderRow
        label="Survival decay alarm"
        value={t.survival}
        min={1}
        max={7}
        step={1}
        display={`${t.survival}d`}
        onChange={(v) => setT((p) => ({ ...p, survival: v }))}
      />
      <div className="pt-2">
        <Button size="sm" variant="ghost" className="text-muted-foreground hover:text-neon" onClick={() => setT(THRESH_DEFAULTS)}>
          <RotateCcw size={14} className="mr-1.5" />
          Reset thresholds
        </Button>
      </div>
    </>
  );
}

function SliderRow({
  label,
  value,
  min,
  max,
  step,
  display,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  display: string;
  onChange: (v: number) => void;
}) {
  return (
    <div>
      <div className="flex items-center justify-between text-xs mb-1.5">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-mono text-neon">{display}</span>
      </div>
      <Slider
        value={[value]}
        min={min}
        max={max}
        step={step}
        onValueChange={(v) => onChange(v[0])}
        className="[&_[role=slider]]:bg-neon [&_[role=slider]]:border-neon"
      />
    </div>
  );
}
