import { createFileRoute } from "@tanstack/react-router";
import { useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { HydraLogo } from "@/components/HydraLogo";

export const Route = createFileRoute("/logo")({
  head: () => ({ meta: [{ title: "HYDRA — Logo" }] }),
  component: LogoPage,
});

function LogoPage() {
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
        {/* particle field */}
        <div className="pointer-events-none absolute inset-0 opacity-[0.07]"
          style={{
            backgroundImage:
              "radial-gradient(1px 1px at 25% 35%, oklch(0.92 0.22 128) 50%, transparent 51%), radial-gradient(1px 1px at 70% 60%, oklch(0.92 0.22 128) 50%, transparent 51%), radial-gradient(1px 1px at 45% 80%, oklch(0.92 0.22 128) 50%, transparent 51%)",
            backgroundSize: "180px 180px, 240px 240px, 300px 300px",
          }}
        />

        {/* controls */}
        <div className="absolute top-6 right-6 z-20 flex items-center gap-2">
          <button onClick={play} data-tour="logo-play"
            className="inline-flex items-center gap-2 rounded-lg border border-neon/40 bg-neon/10 px-3 py-1.5 text-xs text-neon hover:bg-neon/20">
            <Play size={14} /> Play
          </button>
          <button onClick={reset}
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface/60 px-3 py-1.5 text-xs text-muted-foreground hover:text-foreground">
            <RotateCcw size={14} /> Reset
          </button>
        </div>

        {/* center composition */}
        <div className="relative z-10 flex min-h-screen items-center justify-center">
          <div key={runId} className={`relative ${playing ? "logo-stage-play" : "opacity-0"}`}>
            {/* shield glow */}
            <div className="absolute inset-0 -m-32 rounded-full blur-3xl"
              style={{ background: "radial-gradient(closest-side, oklch(0.92 0.22 128 / 0.28), transparent 70%)" }} />
            {/* breathing ring */}
            <div className="absolute inset-0 -m-10 rounded-full border border-neon/20 logo-breathe" />
            <div className="absolute inset-0 -m-20 rounded-full border border-neon/10 logo-breathe" style={{ animationDelay: "0.6s" }} />

            {/* logo + word */}
            <div className="relative flex flex-col items-center gap-6 px-12 py-10">
              <div className="relative">
                <HydraLogo size={140} />
                {/* diagonal shine */}
                <div className="pointer-events-none absolute inset-0 overflow-hidden rounded-full">
                  <div className="logo-shine absolute -inset-y-8 -left-1/2 w-1/2 rotate-[20deg]"
                    style={{
                      background:
                        "linear-gradient(90deg, transparent, oklch(1 0 0 / 0.55), oklch(0.92 0.22 128 / 0.6), transparent)",
                      filter: "blur(6px)",
                    }} />
                </div>
              </div>
              <div className="relative">
                <h1 className="font-display text-7xl tracking-[0.32em] text-neon"
                  style={{ textShadow: "0 0 24px oklch(0.92 0.22 128 / 0.45)" }}>
                  HYDRA
                </h1>
                <div className="pointer-events-none absolute inset-0 overflow-hidden">
                  <div className="logo-shine-text absolute -inset-y-6 -left-1/2 w-1/2 rotate-[20deg]"
                    style={{
                      background:
                        "linear-gradient(90deg, transparent, oklch(1 0 0 / 0.45), transparent)",
                      filter: "blur(4px)",
                    }} />
                </div>
              </div>
              <p className="font-mono text-[11px] tracking-[0.3em] text-muted-foreground/70 uppercase">
                Sovereign · Governed · Auditable
              </p>
            </div>
          </div>
        </div>
      </div>

      <style>{`
        @keyframes logoIn {
          0% { opacity: 0; transform: scale(0.96); filter: blur(8px); }
          100% { opacity: 1; transform: scale(1); filter: blur(0); }
        }
        @keyframes logoShine {
          0% { transform: translateX(-60%) rotate(20deg); opacity: 0; }
          15% { opacity: 1; }
          100% { transform: translateX(420%) rotate(20deg); opacity: 0; }
        }
        @keyframes logoBreathe {
          0%, 100% { transform: scale(1); opacity: 0.6; }
          50% { transform: scale(1.04); opacity: 1; }
        }
        .logo-stage-play { animation: logoIn 1.4s ease-out both; }
        .logo-shine { animation: logoShine 2.6s ease-in-out 1.2s both; }
        .logo-shine-text { animation: logoShine 2.6s ease-in-out 1.6s both; }
        .logo-breathe { animation: logoBreathe 4s ease-in-out 2s infinite; }
      `}</style>
    </AppLayout>
  );
}
