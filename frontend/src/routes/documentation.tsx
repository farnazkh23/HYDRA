import { createFileRoute } from "@tanstack/react-router";
import { useEffect, useRef, useState } from "react";
import { Play, RotateCcw } from "lucide-react";
import { AppLayout } from "@/components/layout/AppLayout";
import { ArchitectureMap } from "@/components/docs/ArchitectureMap";
import { DetailPanel } from "@/components/docs/DetailPanel";
import { advantageCards, allNodes, playSequence } from "@/lib/documentation-data";

export const Route = createFileRoute("/documentation")({
  head: () => ({
    meta: [
      { title: "HYDRA Engine Architecture — System Documentation" },
      {
        name: "description",
        content:
          "How HYDRA's low-cost public intelligence gate and sovereign reasoning engine interact to produce audit-ready compliance decisions.",
      },
      { property: "og:title", content: "HYDRA Engine Architecture" },
      {
        property: "og:description",
        content:
          "Two-layer system blueprint: cheap drift detection feeds sovereign reasoning via DRIFT_EVENT.",
      },
    ],
  }),
  component: DocumentationPage,
});

function DocumentationPage() {
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [visitedIds, setVisitedIds] = useState<string[]>([]);
  const [currentActiveId, setCurrentActiveId] = useState<string | null>(null);
  const [playing, setPlaying] = useState(false);
  const [finished, setFinished] = useState(false);
  const timer = useRef<number | null>(null);

  const selected = selectedId ? allNodes.find((n) => n.id === selectedId) ?? null : null;

  useEffect(() => () => {
    if (timer.current) window.clearInterval(timer.current);
  }, []);

  const play = () => {
    if (playing) return;
    setPlaying(true);
    setFinished(false);
    setSelectedId(null);
    let i = 0;
    const first = playSequence[0];
    setVisitedIds([first]);
    setCurrentActiveId(first);
    timer.current = window.setInterval(() => {
      i += 1;
      if (i >= playSequence.length) {
        if (timer.current) window.clearInterval(timer.current);
        timer.current = null;
        setPlaying(false);
        setFinished(true);
        window.setTimeout(() => setCurrentActiveId(null), 800);
        return;
      }
      setVisitedIds((prev) => [...prev, playSequence[i]]);
      setCurrentActiveId(playSequence[i]);
    }, 650);
  };

  const reset = () => {
    if (timer.current) {
      window.clearInterval(timer.current);
      timer.current = null;
    }
    setPlaying(false);
    setFinished(false);
    setVisitedIds([]);
    setCurrentActiveId(null);
    setSelectedId(null);
    if (typeof window !== "undefined") window.scrollTo({ top: 0, behavior: "smooth" });
  };


  return (
    <AppLayout>
      <div className="px-6 lg:px-10 py-8 max-w-[1600px] mx-auto">
        {/* Header */}
        <div className="mb-6">
          <div className="font-display text-[11px] uppercase tracking-[0.22em] text-neon">
            System Documentation
          </div>
          <h1 className="font-display text-3xl sm:text-4xl mt-1">HYDRA Engine Architecture</h1>
          <p className="text-sm text-muted-foreground mt-2 max-w-3xl">
            How low-cost drift detection and deep sovereign reasoning interact to produce
            audit-ready compliance decisions.
          </p>

          <div className="mt-4 flex flex-wrap items-center gap-3">
            <div className="rounded-lg border border-neon/30 bg-neon-soft px-3 py-2 text-[12px] text-neon max-w-2xl">
              "Most customer signals are stable and dropped cheaply. Only suspicious regime shifts
              are escalated."
            </div>
            <div className="flex gap-2 ml-auto">
              <button
                type="button"
                onClick={play}
                disabled={playing}
                data-tour="doc-play"
                className="inline-flex items-center gap-2 rounded-lg border border-neon/40 bg-neon-soft px-3 py-1.5 text-[12px] text-neon hover-lift disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Play size={14} /> {playing ? "Playing…" : "Play pipeline"}
              </button>
              <button
                type="button"
                onClick={reset}
                className="inline-flex items-center gap-2 rounded-lg border border-border bg-surface-2 px-3 py-1.5 text-[12px] text-muted-foreground hover-lift"
              >
                <RotateCcw size={14} /> Reset view
              </button>
            </div>
          </div>
        </div>

        {/* Main blueprint + detail panel */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_360px] gap-6">
          <ArchitectureMap
            selectedId={selectedId}
            visitedIds={visitedIds}
            currentActiveId={currentActiveId}
            onSelect={(id) => setSelectedId((cur) => (cur === id ? null : id))}
          />
          <div className="lg:sticky lg:top-6 self-start">
            <DetailPanel node={selected} />
          </div>
        </div>

        {/* Business advantages */}
        <div className="mt-6 lg:max-w-[calc(100%-360px-1.5rem)]">
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {advantageCards.map((c) => (
              <div
                key={c.title}
                className={`rounded-xl border bg-card/60 backdrop-blur p-4 hover-lift transition-all ${
                  finished
                    ? "border-neon shadow-[0_0_20px_oklch(0.92_0.22_128/0.35)]"
                    : "border-neon/30"
                }`}
              >
                <div className="font-display text-[10px] uppercase tracking-[0.22em] text-neon">
                  Advantage
                </div>
                <div className="font-display text-sm mt-1">{c.title}</div>
                <div className="text-[11px] text-muted-foreground mt-1 leading-snug">
                  {c.body}
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </AppLayout>
  );
}
