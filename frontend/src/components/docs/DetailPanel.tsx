import type { DocNode } from "@/lib/documentation-data";

export function DetailPanel({ node }: { node: DocNode | null }) {
  if (!node) {
    return (
      <div className="rounded-2xl border border-border bg-card/60 backdrop-blur p-6 text-sm text-muted-foreground">
        <div className="font-display text-[11px] uppercase tracking-[0.18em] text-neon mb-2">
          Detail panel
        </div>
        <p>
          Click any component, layer, the DRIFT_EVENT bridge, or the audit output to inspect its
          role, inputs, outputs, and why it matters for compliance.
        </p>
      </div>
    );
  }

  return (
    <div className="rounded-2xl border border-neon/30 bg-card/70 backdrop-blur p-6 space-y-4">
      <div>
        <div className="font-display text-[11px] uppercase tracking-[0.18em] text-neon">
          {node.layer === "bridge"
            ? "Bridge"
            : node.layer === "input"
            ? "Input"
            : node.layer === "output"
            ? "Output"
            : `Layer ${node.layer}`}
        </div>
        <h3 className="font-display text-xl mt-1 leading-tight">{node.title}</h3>
      </div>

      <Row label="Role" value={node.role} />
      <Row label="Consumes" value={node.consumes} />
      <Row label="Produces" value={node.produces} />
      <Row label="Why it matters" value={node.why} />
    </div>
  );
}

function Row({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.18em] text-muted-foreground mb-1">
        {label}
      </div>
      <div className="text-sm text-foreground/90 leading-relaxed">{value}</div>
    </div>
  );
}
