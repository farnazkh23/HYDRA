import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { HydraLogo } from "@/components/HydraLogo";

export const Route = createFileRoute("/closing")({
  head: () => ({ meta: [{ title: "HYDRA — Closing" }] }),
  component: ClosingPage,
});

function ClosingPage() {
  const [runId, setRunId] = useState(0);
  const [playing, setPlaying] = useState(false);

  const play = () => {
    setPlaying(false);
    requestAnimationFrame(() => {
      setRunId((n) => n + 1);
      setPlaying(true);
    });
  };
  const reset = () => {
    setPlaying(false);
    setRunId((n) => n + 1);
  };

  return (
    <AppLayout>
      <div className="relative min-h-screen w-full overflow-hidden bg-background grid-bg">
        <div className="absolute top-6 right-6 z-20 flex items-center gap-2">
          <button onClick={play} data-tour="closing-play"
            className="inline-flex items-center gap-2 rounded-lg border border-neon/40 bg-neon/10 px-3 py-1.5 text-xs text-neon hover:bg-neon/20">
            <Play size={14} /> Play
          </button>
          <button onClick={reset}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface/60 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
            <RotateCcw size={14} /> Reset
          </button>
        </div>

        <div className="relative z-10 flex min-h-screen items-center justify-center">
          <div key={runId} className={`relative flex flex-col items-center gap-10 px-8 ${playing ? "closing-bg-in" : "opacity-0"}`}>
            {/* logo */}
            <div className="relative closing-logo-in">
              <div className="absolute inset-0 -m-28 rounded-full blur-3xl"
                style={{ background: "radial-gradient(closest-side, oklch(0.92 0.22 128 / 0.28), transparent 70%)" }} />
              <div className="absolute inset-0 -m-8 rounded-full border border-neon/20 closing-breathe" />
              <div className="relative flex flex-col items-center gap-4">
                <HydraLogo size={110} />
                <div className="relative">
                  <h1 className="font-display text-6xl tracking-[0.32em] text-neon"
                    style={{ textShadow: "0 0 24px oklch(0.92 0.22 128 / 0.45)" }}>
                    HYDRA
                  </h1>
                  <div className="pointer-events-none absolute inset-0 overflow-hidden">
                    <div className="closing-shine absolute -inset-y-8 -left-1/2 w-1/2 rotate-[20deg]"
                      style={{
                        background:
                          "linear-gradient(90deg, transparent, oklch(1 0 0 / 0.55), oklch(0.92 0.22 128 / 0.6), transparent)",
                        filter: "blur(6px)",
                      }} />
                  </div>
                </div>
              </div>
            </div>

            {/* slogan */}
            <p className="closing-slogan-in max-w-3xl text-center font-display text-xl leading-snug text-foreground/95 whitespace-nowrap">
              Many heads. <span className="text-neon">One governed warning.</span> Full risk visibilty.
            </p>

            <p className="closing-line-in font-mono text-sm tracking-[0.2em] uppercase text-muted-foreground">
              Catch KYC drift before risk crystallises.
            </p>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes closingBg { from { opacity: 0; } to { opacity: 1; } }
        @keyframes closingLogo {
          0% { opacity: 0; transform: scale(0.96); filter: blur(8px); }
          100% { opacity: 1; transform: scale(1); filter: blur(0); }
        }
        @keyframes closingShine {
          0% { transform: translateX(-60%) rotate(20deg); opacity: 0; }
          15% { opacity: 1; }
          100% { transform: translateX(420%) rotate(20deg); opacity: 0; }
        }
        @keyframes closingFadeUp {
          0% { opacity: 0; transform: translateY(12px); }
          100% { opacity: 1; transform: translateY(0); }
        }
        @keyframes closingBreathe {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.04); opacity: 1; }
        }
        .closing-bg-in { animation: closingBg 0.8s ease-out both; }
        .closing-logo-in { animation: closingLogo 1.4s ease-out 0.3s both; }
        .closing-shine { animation: closingShine 2.6s ease-in-out 1.6s both; }
        .closing-slogan-in { animation: closingFadeUp 1s ease-out 2.8s both; }
        .closing-line-in { animation: closingFadeUp 1s ease-out 3.8s both; }
        .closing-breathe { animation: closingBreathe 4s ease-in-out 2.5s infinite; }
      `}</style>
    </AppLayout>
  );
}
