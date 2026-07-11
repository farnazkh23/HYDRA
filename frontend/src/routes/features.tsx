import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Play, RotateCcw, CheckCircle2 } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";

export const Route = createFileRoute("/features")({
  head: () => ({ meta: [{ title: "HYDRA — Features" }] }),
  component: FeaturesPage,
});

const ARCH_TEXT = `HYDRA is a multi-layered intelligence engine, not a single-model alert system. It orchestrates specialized layers for drift detection, graph reasoning, forecasting, routing, guardrails, and governed output.`;

const PIPELINE = [
  "SPLADE",
  "Transformer embeddings",
  "VAE drift detection",
  "FAST classifiers",
  "Temporal GraphRAG",
  "TimeGPT",
  "Sovereign Apertus-8B reasoning",
  "Guardrails",
  "Governed output",
];

const ADVANTAGES = [
  {
    title: "Operational Expense",
    body: "Noise gets filtered locally before expensive AI is triggered — turning heavy news cycles into controlled compute costs.",
  },
  {
    title: "Risk Visibility",
    body: "Risk is turned into a timeline, not a surprise — showing how fast exposure is deteriorating and when intervention is needed.",
  },
  {
    title: "Alert Accuracy",
    body: "Every alert is grounded in a strict knowledge graph representation of entities, relationships, and evidence — ensuring structured, interpretable output while reducing hallucinations, false positives, and analyst fatigue.",
  },
  {
    title: "System Flexibility",
    body: "Models and components are upgraded through modular layers, not platform rebuilds — allowing the system to evolve without downtime.",
  },
  {
    title: "Regulatory Trust",
    body: "Critical reasoning stays inside sovereign Swiss infrastructure with local fallback — protecting compliance continuity when reliability matters most.",
  },
];

const DEFAULT_TYPE_SPEED = 60; // ms per char — talking speed
// Cumulative delays (ms) after pipeline finishes for each advantage card.
// Deltas requested: +0, +5s, +4s, +8s, +8s
const DEFAULT_CARD_DELAYS = [0, 5000, 9000, 17000, 25000];
const FAST_CARD_DELAYS = [0, 1600, 3200, 4800, 6400];

function FeaturesPage() {
  const [typed, setTyped] = useState("");
  const [pipeIdx, setPipeIdx] = useState(-1);
  const [cardIdx, setCardIdx] = useState(-1);
  const [phase, setPhase] = useState<"idle" | "running" | "done">("idle");
  const timers = useRef<ReturnType<typeof setTimeout>[]>([]);

  const clearAll = () => {
    timers.current.forEach(clearTimeout);
    timers.current = [];
  };
  useEffect(() => () => clearAll(), []);

  const reset = () => {
    clearAll();
    setTyped("");
    setPipeIdx(-1);
    setCardIdx(-1);
    setPhase("idle");
  };

  const play = () => {
    reset();
    setPhase("running");
    const fast =
      typeof window !== "undefined" &&
      (window as unknown as { __HYDRA_TOUR_FAST?: boolean }).__HYDRA_TOUR_FAST === true;
    const TYPE_SPEED = fast ? 28 : DEFAULT_TYPE_SPEED;
    const CARD_DELAYS = fast ? FAST_CARD_DELAYS : DEFAULT_CARD_DELAYS;
    const startDelay = 600;
    const typingDuration = ARCH_TEXT.length * TYPE_SPEED;

    // type the architecture text
    let i = 0;
    const tick = () => {
      i++;
      setTyped(ARCH_TEXT.slice(0, i));
      if (i < ARCH_TEXT.length) {
        timers.current.push(setTimeout(tick, TYPE_SPEED));
      }
    };
    timers.current.push(setTimeout(tick, startDelay));

    // Pipeline boxes light up progressively WHILE the text is being typed
    PIPELINE.forEach((_, idx) => {
      const t = startDelay + ((idx + 1) / PIPELINE.length) * typingDuration;
      timers.current.push(setTimeout(() => setPipeIdx(idx), t));
    });

    const afterPipe = startDelay + typingDuration + 400;
    ADVANTAGES.forEach((_, idx) => {
      timers.current.push(setTimeout(() => setCardIdx(idx), afterPipe + CARD_DELAYS[idx]));
    });
    timers.current.push(
      setTimeout(() => setPhase("done"), afterPipe + CARD_DELAYS[CARD_DELAYS.length - 1] + 500),
    );
  };

  return (
    <AppLayout>
      <div className="min-h-screen bg-background text-foreground">
        <div className="mx-auto max-w-[1600px] px-8 py-8">
          {/* header */}
          <div className="flex items-center justify-between border-b border-neon/20 pb-4">
            <div className="flex items-center gap-3 font-mono text-xs text-neon">
              <span className="h-2 w-2 rounded-full bg-neon shadow-[0_0_10px_oklch(0.92_0.22_128/0.8)]" />
              <span className="tracking-[0.25em]">HYDRA MULTILAYER INTELLIGENCE STACK</span>
              <span className="text-muted-foreground">— /pipeline/run</span>
            </div>
            <div className="flex gap-2">
              <button onClick={play} data-tour="features-play"
                className="inline-flex items-center gap-2 rounded-lg border border-neon/40 bg-neon/10 px-3 py-1.5 text-xs text-neon hover:bg-neon/20">
                <Play size={14} /> Play
              </button>
              <button onClick={reset}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface/60 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
                <RotateCcw size={14} /> Reset
              </button>
            </div>
          </div>

          {/* terminal */}
          <div className="mt-6 rounded-xl border border-neon/20 bg-[oklch(0.14_0.005_240)] p-6 shadow-[inset_0_0_60px_oklch(0.92_0.22_128/0.04)]">
            <div className="font-mono text-sm leading-7 text-neon/90">
              <span className="text-muted-foreground">hydra@core:~$ </span>
              <span>describe --stack</span>
            </div>
            <div className="mt-3 font-mono text-[15px] leading-8 text-neon">
              {typed}
              {phase === "running" && typed.length < ARCH_TEXT.length && (
                <span className="ml-0.5 inline-block h-4 w-2 -mb-0.5 bg-neon animate-pulse" />
              )}
            </div>
          </div>

          {/* pipeline */}
          <div className="mt-6 grid grid-cols-3 gap-3 md:grid-cols-5 lg:grid-cols-9">
            {PIPELINE.map((label, i) => {
              const on = pipeIdx >= i;
              return (
                <div key={label}
                  className={`relative rounded-lg border px-3 py-3 text-center font-mono text-[11px] transition-all duration-300 ${
                    on
                      ? "border-neon/70 bg-neon/10 text-neon shadow-[0_0_18px_oklch(0.92_0.22_128/0.35)]"
                      : "border-border bg-surface/40 text-muted-foreground"
                  }`}>
                  <div className="text-[9px] opacity-60">L{i + 1}</div>
                  <div className="mt-1 leading-tight">{label}</div>
                  {on && (
                    <div className="absolute -bottom-1 left-1/2 h-1 w-6 -translate-x-1/2 rounded-full bg-neon/70" />
                  )}
                </div>
              );
            })}
          </div>

          {/* advantages intro */}
          {phase === "done" ? (
            <div className="mt-8 font-mono text-xs text-muted-foreground">
              <span className="text-neon">hydra@core:~$ </span>
              HYDRA translates this architecture into five clear business advantages:
            </div>
          ) : (
            <div className="mt-8 h-4" />
          )}

          {/* cards */}
          <div className="mt-4 grid grid-cols-1 gap-4 md:grid-cols-2 xl:grid-cols-5">
            {ADVANTAGES.map((a, i) => {
              const on = cardIdx >= i;
              return (
                <div key={a.title}
                  className={`rounded-xl border p-5 transition-all duration-700 ${
                    on
                      ? "border-neon/60 bg-neon/[0.06] opacity-100 translate-y-0 shadow-[0_0_24px_oklch(0.92_0.22_128/0.18)]"
                      : "border-border bg-surface/30 opacity-0 translate-y-3"
                  }`}>
                  <div className="flex items-center gap-2 text-neon">
                    <CheckCircle2 size={16} />
                    <span className="font-display text-sm tracking-wider uppercase">{a.title}</span>
                  </div>
                  <p className="mt-3 text-sm leading-6 text-foreground/85">{a.body}</p>
                  <div className="mt-4 font-mono text-[10px] text-muted-foreground">
                    advantage_0{i + 1} :: ok
                  </div>
                </div>
              );
            })}
          </div>

          {/* status */}
          {phase === "done" ? (
            <div className="mt-6 font-mono text-xs text-muted-foreground">
              <span className="text-neon">hydra@core:~$ </span>
              <span className="text-neon">pipeline complete — 9 layers online · 5 advantages confirmed</span>
            </div>
          ) : phase === "running" ? (
            <div className="mt-6 font-mono text-xs text-muted-foreground">
              <span className="text-neon">hydra@core:~$ </span>
              running<span className="animate-pulse">…</span>
            </div>
          ) : (
            <div className="mt-6 font-mono text-xs text-muted-foreground">
              <span className="text-neon">hydra@core:~$ </span>
              awaiting input · press Play
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
