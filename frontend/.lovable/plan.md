## Documentation Page — Refined Concept

A new `/documentation` route added after Settings in the sidebar. Not a docs page — a **live system blueprint** of the HYDRA engine, rendered in the existing dark charcoal + neon-lime aesthetic.

---

### 1. Page Structure

```text
┌─────────────────────────────────────────────────────────┐
│ EYEBROW: SYSTEM DOCUMENTATION                           │
│ H1: HYDRA Engine Architecture                           │
│ Subtitle + compact insight card                         │
│ [ ▶ Play pipeline ]  [ ⟳ Reset view ]                  │
├─────────────────────────────────────────────────────────┤
│  ┌─ Blueprint canvas (2/3) ──┐ ┌─ Detail panel (1/3) ─┐│
│  │  RAW PUBLIC SIGNALS pill  │ │  Component name      ││
│  │           │               │ │  Role                ││
│  │  ╔═════ LAYER 1 ════════╗ │ │  Consumes            ││
│  │  ║ 8 component cards   ║ │ │  Produces            ││
│  │  ║ + stable/suspicious ║ │ │  Why it matters      ││
│  │  ║   branching paths   ║ │ │                      ││
│  │  ║ + metric chips      ║ │ │  (sticky, scrolls    ││
│  │  ╚═════════════════════╝ │ │   independently)     ││
│  │           │               │ │                      ││
│  │  ◆ DRIFT_EVENT PAYLOAD ◆ │ │                      ││
│  │           │               │ │                      ││
│  │  ╔═════ LAYER 2 ════════╗ │ │                      ││
│  │  ║ 7 component cards   ║ │ │                      ││
│  │  ║ + T decision diamond║ │ │                      ││
│  │  ╚═════════════════════╝ │ │                      ││
│  │           │               │ │                      ││
│  │  ▣ AUDIT-READY OUTPUT    │ │                      ││
│  └───────────────────────────┘ └──────────────────────┘│
└─────────────────────────────────────────────────────────┘
```

Mobile: detail panel slides up as a sheet from bottom when a card is tapped.

---

### 2. Visual Language (reuses existing tokens — no new theme)

- **Layer containers**: `bg-card/60` glass + `border-neon/30`, inner `grid-bg`, uppercase Space Grotesk title, one-line subtitle.
- **Component cards**: `bg-surface-2`, 1px `border-border`, hover → `border-neon/60` + soft lime glow (`hover-lift` utility already exists).
- **Connector lines**: thin SVG paths, `stroke-neon/40`; stable path uses `stroke-muted-foreground/40` with label "Stable signal → dropped cheaply"; suspicious path glows neon-lime with label "Suspicious signal → DRIFT_EVENT emitted".
- **DRIFT_EVENT bridge card**: prominent centered diamond/pill with `lime-outline` (utility already exists), example fields rendered as small chips.
- **T-decision diamond**: rotated square in Layer 2 splitting into "T ≥ 7d" (muted) vs "T < 7d" (neon-red glow into Apertus card).
- **Final output**: full-width card under Layer 2 with 5 chips (Risk Token, Audit Summary, Citations, Budget, Action).
- Light-mode handled automatically by existing `--neon`, `--surface-2`, `--border` tokens; no hardcoded colors.

---

### 3. Interaction

- **Click a card** → updates right-side detail panel (no modal, no route change). Selected card gets `lime-outline` + ring.
- **Hover** → border brighten + 200ms neon glow via existing `hover-lift`.
- **▶ Play pipeline** → sequentially pulses Raw Signals → each Layer 1 card → DRIFT_EVENT → each Layer 2 card → Audit Output. Uses CSS class toggles on a 350ms-per-step interval. Disable button while playing.
- **⟳ Reset view** → clears selection, stops animation, scrolls canvas to top.
- All 15+ components, the 2 layers, the DRIFT_EVENT bridge, and the Audit Output are selectable (17 detail entries total).

---

### 4. Content Data

A single `documentation-data.ts` module exports a typed array of nodes:

```ts
type DocNode = {
  id: string;
  layer: 1 | 2 | "bridge" | "input" | "output";
  title: string;
  short: string;           // one-line on card
  role: string;            // detail panel
  consumes: string;
  produces: string;
  why: string;
};
```

All copy (Layer 1's 8 cards, Layer 2's 7 cards, DRIFT_EVENT example fields, Audit Output chips, and the two umbrella Layer entries) comes from this file — easy to edit later.

---

### 5. Files to add / edit

- **new** `src/routes/documentation.tsx` — route + page
- **new** `src/components/docs/ArchitectureMap.tsx` — blueprint canvas (layers, SVG connectors, animation controller)
- **new** `src/components/docs/ComponentCard.tsx` — reusable hoverable card
- **new** `src/components/docs/DetailPanel.tsx` — sticky right panel
- **new** `src/lib/documentation-data.ts` — all copy
- **edit** `src/components/layout/Sidebar.tsx` — add "Documentation" item after Settings (icon: `BookOpen`)

No changes to theme, routing infra, logo, other routes, or business logic.

---

### Open questions before I build

1. **Sidebar order** — you previously asked for `Dashboard / Alerts / Customers / Reports / Logs / Settings`. Confirm Documentation goes at the very bottom (after Settings), or should it sit between Logs and Settings?
2. **"Play pipeline" speed** — default to ~350ms per step (~6s total run). OK or do you want it slower/faster?
3. **Connector rendering** — SVG paths inside the canvas (precise, animatable) vs simple CSS arrows between divs (lighter, less precise). I recommend SVG. Confirm?

Reply with answers (or "go" to accept defaults: bottom of sidebar, 350ms, SVG) and I'll build it.
