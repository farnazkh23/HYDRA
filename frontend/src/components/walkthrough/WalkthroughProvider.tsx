import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { useNavigate } from "@tanstack/react-router";
import {
  ChevronDown,
  ChevronUp,
  MousePointer2,
  Pencil,
  Play,
  SkipForward,
  Square,
} from "lucide-react";

type Action =
  | { type: "moveTo"; at: number; selector?: string; xy?: [number, number] }
  | { type: "click"; at: number; selector: string }
  | { type: "pulse"; at: number };

type Step = {
  id: string;
  label: string;
  route?: string;
  text?: string;
  preDelay?: number;
  postDelay?: number;
  duration?: number;
  actions?: Action[];
};

// Visual-only walkthrough. The presenter reads the text aloud; the UI shows
// the line on-screen and drives the cursor + clicks in sync.
const INITIAL_SCRIPT: Step[] = [
  {
    id: "intro-q",
    label: "Intro · question",
    route: "/logo",
    text: "How do we capture something constantly evolving — and so scattered?",
    preDelay: 600,
    duration: 6500,
  },
  {
    id: "intro-hydra",
    label: "Intro · Hydra reveal",
    text: "Hydra.",
    preDelay: 200,
    duration: 6000,
    actions: [
      { type: "moveTo", at: 0, selector: '[data-tour="logo-play"]' },
      { type: "click", at: 250, selector: '[data-tour="logo-play"]' },
    ],
  },
  {
    id: "dashboard",
    label: "Dashboard · live graph",
    route: "/",
    text: "The dashboard shows a live graph of monitored clients and entities. As the world changes, Hydra updates the risk network in real time — like this new offshore link.",
    preDelay: 800,
    duration: 14000,
    actions: [
      { type: "moveTo", at: 600, selector: '[data-node-id="spacex"]' },
      { type: "pulse", at: 1400 },
      { type: "moveTo", at: 4500, selector: '[data-node-id="offshore"]' },
      { type: "pulse", at: 5200 },
      { type: "moveTo", at: 9500, selector: '[data-tour="latest-alert"]' },
      { type: "pulse", at: 10200 },
      { type: "click", at: 12000, selector: '[data-tour="latest-alert"]' },
    ],
  },
  {
    id: "alerts",
    label: "Alerts · open investigation",
    text: "The alerts queue surfaces the latest drift events. Let's open the top investigation.",
    preDelay: 700,
    duration: 5500,
    actions: [
      { type: "moveTo", at: 400, selector: '[data-alert-row="alert_001"]' },
      { type: "pulse", at: 1200 },
      { type: "click", at: 3200, selector: '[data-alert-row="alert_001"]' },
    ],
  },
  {
    id: "investigation",
    label: "Investigation · evidence",
    text: "Inside the case, Hydra shows what changed, why it was flagged, the reasoning trace, the supporting evidence, and the analyst actions — every decision auditable.",
    preDelay: 800,
    duration: 13000,
  },
  {
    id: "customer",
    label: "Customer · SpaceX profile",
    route: "/customers/spacex",
    text: "The customer profile updates immediately — risk score, drift, verification status, and recent alerts all reflect live reality.",
    preDelay: 700,
    duration: 11000,
  },
  {
    id: "reports",
    label: "Reports · audit-ready",
    route: "/reports",
    text: "Reports turn each case into audit-ready evidence for compliance review.",
    preDelay: 600,
    duration: 7000,
  },
  {
    id: "pipeline",
    label: "Pipeline · engine",
    route: "/documentation",
    text: "Behind the interface, Hydra's pipeline runs cheap drift detection feeding sovereign reasoning — from raw signals to governed output, end to end.",
    preDelay: 900,
    duration: 22000,
    actions: [
      { type: "moveTo", at: 400, selector: '[data-tour="doc-play"]' },
      { type: "click", at: 1100, selector: '[data-tour="doc-play"]' },
    ],
  },
  {
    id: "features",
    label: "Features · advantages",
    route: "/features",
    text: "Hydra is a multi-layered intelligence engine — drift detection, graph reasoning, forecasting, routing, guardrails, and governed output. Five advantages: noise filtered locally, risk on a timeline, alerts grounded in a knowledge graph, modular upgrades, and sovereign Swiss reasoning.",
    preDelay: 900,
    duration: 28000,
    actions: [
      { type: "moveTo", at: 300, selector: '[data-tour="features-play"]' },
      { type: "click", at: 900, selector: '[data-tour="features-play"]' },
    ],
  },
  {
    id: "closing",
    label: "Closing · slogan",
    route: "/closing",
    text: "Hydra. Many heads. One governed warning. Full risk visibility.",
    preDelay: 900,
    duration: 9000,
    postDelay: 1000,
    actions: [
      { type: "moveTo", at: 250, selector: '[data-tour="closing-play"]' },
      { type: "click", at: 800, selector: '[data-tour="closing-play"]' },
    ],
  },
];

type Ctx = {
  active: boolean;
  index: number;
  total: number;
  currentText: string | null;
  script: Step[];
  updateStepText: (id: string, text: string) => void;
  start: () => void;
  stop: () => void;
  next: () => void;
};

const WalkthroughCtx = createContext<Ctx | null>(null);

export function useWalkthrough() {
  const c = useContext(WalkthroughCtx);
  if (!c) throw new Error("WalkthroughProvider missing");
  return c;
}

const wait = (ms: number) => new Promise<void>((r) => setTimeout(r, ms));

function selectorToXY(selector?: string): [number, number] | null {
  if (!selector || typeof document === "undefined") return null;
  const el = document.querySelector(selector) as HTMLElement | SVGElement | null;
  if (!el) return null;
  const r = el.getBoundingClientRect();
  return [r.left + r.width / 2, r.top + r.height / 2];
}

type CursorState = { x: number; y: number; visible: boolean; clicking: boolean };

export function WalkthroughProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate();
  const [active, setActive] = useState(false);
  const [index, setIndex] = useState(-1);
  const [currentText, setCurrentText] = useState<string | null>(null);
  const [script, setScript] = useState<Step[]>(INITIAL_SCRIPT);
  const scriptRef = useRef<Step[]>(INITIAL_SCRIPT);
  const [cursor, setCursor] = useState<CursorState>({
    x: 0,
    y: 0,
    visible: false,
    clicking: false,
  });

  const cancelRef = useRef(false);
  const skipRef = useRef<(() => void) | null>(null);

  const updateStepText = useCallback((id: string, text: string) => {
    setScript((prev) => {
      const next = prev.map((s) => (s.id === id ? { ...s, text } : s));
      scriptRef.current = next;
      return next;
    });
  }, []);

  const waitOrSkip = useCallback(async (ms: number): Promise<void> => {
    if (ms <= 0) return;
    await new Promise<void>((resolve) => {
      let done = false;
      const finish = () => {
        if (done) return;
        done = true;
        skipRef.current = null;
        clearTimeout(handle);
        resolve();
      };
      const handle = setTimeout(finish, ms);
      skipRef.current = finish;
    });
  }, []);

  const execAction = useCallback(async (a: Action) => {
    if (a.type === "moveTo") {
      const xy = a.xy ?? selectorToXY(a.selector);
      if (xy) setCursor((c) => ({ ...c, x: xy[0], y: xy[1], visible: true }));
      return;
    }
    if (a.type === "pulse") {
      setCursor((c) => ({ ...c, clicking: true, visible: true }));
      await wait(380);
      setCursor((c) => ({ ...c, clicking: false }));
      return;
    }
    if (a.type === "click") {
      const el = document.querySelector(a.selector) as HTMLElement | null;
      const xy = selectorToXY(a.selector);
      if (xy) setCursor((c) => ({ ...c, x: xy[0], y: xy[1], visible: true, clicking: true }));
      await wait(220);
      if (el) {
        try {
          el.click();
        } catch {
          /* noop */
        }
      }
      await wait(180);
      setCursor((c) => ({ ...c, clicking: false }));
    }
  }, []);

  const runStep = useCallback(
    async (i: number) => {
      if (cancelRef.current) return;
      const step = scriptRef.current[i];
      setIndex(i);
      setCurrentText(step.text ?? null);
      if (step.route) {
        try {
          await navigate({ to: step.route });
        } catch {
          /* noop */
        }
      }
      await wait(step.preDelay ?? 400);
      if (cancelRef.current) return;

      const actionTasks = (step.actions ?? []).map((a) =>
        wait(a.at).then(() => execAction(a)),
      );
      const durationTask = waitOrSkip(step.duration ?? 4000);

      await Promise.all([durationTask, ...actionTasks]);
      if (cancelRef.current) return;
      await wait(step.postDelay ?? 150);
    },
    [navigate, execAction, waitOrSkip],
  );

  const stop = useCallback(() => {
    cancelRef.current = true;
    skipRef.current?.();
    if (typeof window !== "undefined") {
      (window as unknown as { __HYDRA_TOUR_FAST?: boolean }).__HYDRA_TOUR_FAST = false;
    }
    setActive(false);
    setIndex(-1);
    setCurrentText(null);
    setCursor((c) => ({ ...c, visible: false, clicking: false }));
  }, []);

  const start = useCallback(async () => {
    cancelRef.current = false;
    scriptRef.current = script;
    if (typeof window !== "undefined") {
      (window as unknown as { __HYDRA_TOUR_FAST?: boolean }).__HYDRA_TOUR_FAST = true;
    }
    setActive(true);
    setCursor({
      x: typeof window !== "undefined" ? window.innerWidth / 2 : 600,
      y: typeof window !== "undefined" ? window.innerHeight / 2 : 400,
      visible: true,
      clicking: false,
    });
    for (let i = 0; i < scriptRef.current.length; i++) {
      if (cancelRef.current) break;
      await runStep(i);
    }
    if (!cancelRef.current) stop();
  }, [runStep, stop, script]);

  const next = useCallback(() => {
    skipRef.current?.();
  }, []);

  useEffect(
    () => () => {
      cancelRef.current = true;
    },
    [],
  );

  return (
    <WalkthroughCtx.Provider
      value={{
        active,
        index,
        total: script.length,
        currentText,
        script,
        updateStepText,
        start,
        stop,
        next,
      }}
    >
      {children}
      <VirtualCursor state={cursor} />
      <WalkthroughBar />
    </WalkthroughCtx.Provider>
  );
}

function VirtualCursor({ state }: { state: CursorState }) {
  if (!state.visible) return null;
  return (
    <div
      className="pointer-events-none fixed z-[70]"
      style={{
        left: 0,
        top: 0,
        transform: `translate3d(${state.x}px, ${state.y}px, 0)`,
        transition: "transform 600ms cubic-bezier(0.45, 0, 0.2, 1)",
      }}
    >
      <div className="relative -translate-x-1 -translate-y-1">
        {state.clicking && (
          <span className="absolute -inset-3 rounded-full border-2 border-neon/80 animate-ping" />
        )}
        <span
          className="absolute -inset-2 rounded-full bg-neon/30 blur-md"
          aria-hidden="true"
        />
        <MousePointer2
          size={22}
          className="relative text-neon drop-shadow-[0_0_6px_oklch(0.92_0.22_128/0.9)]"
          fill="currentColor"
        />
      </div>
    </div>
  );
}

function WalkthroughBar() {
  const w = useWalkthrough();
  const [editorOpen, setEditorOpen] = useState(false);
  const progress = w.active ? ((w.index + 1) / w.total) * 100 : 0;

  return (
    <div className="fixed bottom-4 right-4 z-[60] w-[min(320px,calc(100vw-24px))] rounded-lg border border-neon/30 bg-background/95 p-2 text-xs shadow-xl backdrop-blur-md">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2 font-mono text-[10px] tracking-[0.22em] text-neon uppercase">
          <span className={`h-2 w-2 rounded-full bg-neon shadow-[0_0_10px_oklch(0.92_0.22_128/0.8)] ${w.active ? "animate-pulse" : "opacity-60"}`} />
          {w.active ? `Tour · ${w.index + 1} / ${w.total}` : "Guided tour"}
        </div>
        <div className="flex items-center gap-1.5">
          {!w.active ? (
            <button
              onClick={w.start}
              className="inline-flex items-center gap-1.5 rounded-md border border-neon/50 bg-neon/10 px-3 py-1.5 text-xs font-medium text-neon hover:bg-neon/20"
            >
              <Play size={12} className="fill-current" /> Start
            </button>
          ) : (
            <>
              <button
                onClick={w.next}
                className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
              >
                <SkipForward size={12} /> Next
              </button>
              <button
                onClick={w.stop}
                className="inline-flex items-center gap-1 rounded-md border border-[color:var(--risk-high)]/40 bg-[color:var(--risk-high)]/10 px-2 py-1 text-xs text-[color:var(--risk-high)]"
              >
                <Square size={12} /> End
              </button>
            </>
          )}
          <button
            onClick={() => setEditorOpen((o) => !o)}
            className="inline-flex items-center gap-1 rounded-md border border-border px-2 py-1 text-xs text-muted-foreground hover:text-foreground"
            aria-label="Edit script"
          >
            <Pencil size={12} />
            {editorOpen ? <ChevronDown size={12} /> : <ChevronUp size={12} />}
          </button>
        </div>
      </div>

      {w.active && w.currentText && (
        <p className="mt-2 text-sm leading-6 text-foreground/95">{w.currentText}</p>
      )}

      {w.active && (
        <div className="mt-2 h-1 w-full overflow-hidden rounded-full bg-surface">
          <div
            className="h-full bg-neon transition-all duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      )}

      {editorOpen && (
        <div className="mt-3 max-h-[40vh] space-y-2 overflow-y-auto border-t border-border/60 pt-3">
          {w.script.map((s, i) => (
            <div
              key={s.id}
              className={`rounded-md border p-2 ${
                w.active && i === w.index
                  ? "border-neon/60 bg-neon/5"
                  : "border-border/60 bg-surface/40"
              }`}
            >
              <div className="mb-1 flex items-center justify-between font-mono text-[10px] uppercase tracking-[0.18em] text-muted-foreground">
                <span>
                  {i + 1}. {s.label}
                </span>
                {s.route && <span className="normal-case tracking-normal">{s.route}</span>}
              </div>
              <textarea
                value={s.text ?? ""}
                onChange={(e) => w.updateStepText(s.id, e.target.value)}
                rows={2}
                className="w-full resize-y rounded border border-border/60 bg-background/80 px-2 py-1 text-xs text-foreground/95 outline-none focus:border-neon/60"
              />
            </div>
          ))}
          <p className="text-[10px] text-muted-foreground">
            Edits show on screen as the on-air subtitle while you narrate.
          </p>
        </div>
      )}
    </div>
  );
}
