import type { DocNode } from "@/lib/documentation-data";

export function ComponentCard({
  node,
  selected,
  visited,
  active,
  critical,
  onClick,
}: {
  node: DocNode;
  selected?: boolean;
  visited?: boolean;
  active?: boolean;
  critical?: boolean;
  onClick: (id: string) => void;
}) {
  return (
    <button
      type="button"
      onClick={() => onClick(node.id)}
      className={`group text-left w-full rounded-lg border bg-surface-2/80 px-3 py-2.5 transition-all hover-lift ${
        selected
          ? "lime-outline"
          : critical && (visited || active)
          ? "border-[color:var(--risk-high)]/50"
          : visited
          ? "border-neon/40"
          : "border-border"
      } ${active ? "ring-2 ring-neon/60 shadow-[0_0_24px_oklch(0.92_0.22_128/0.35)]" : ""}`}
    >
      <div className="font-display text-[12px] uppercase tracking-wider text-foreground/95">
        {node.title}
      </div>
      <div className="mt-1 text-[11px] leading-snug text-muted-foreground line-clamp-2">
        {node.short}
      </div>
    </button>
  );
}
