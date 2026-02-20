# Low-Level Design — Frontend (NextJS)

## 1. Purpose

The frontend is a NextJS app (App Router) that provides:
1. A ticker input page
2. A real-time pipeline visualization dashboard with zoom-in/zoom-out per layer
3. A results view showing top 3 + other 12 moves

**Design principles:** Minimal text. Dark theme. Sci-fi/techy aesthetic. **Ultra-smooth zoom transitions** are the hero of the UI.

---

## 2. Tech Stack

| | Technology |
|---|---|
| Framework | NextJS 14+ (App Router) |
| Styling | Tailwind CSS |
| UI Components | shadcn/ui |
| Animations | Framer Motion |
| State Management | React hooks (useSSE, useAnalysis, usePipelineZoom) |
| Real-time | EventSource (SSE) |
| Charts | Recharts (for score breakdown radar/bar) |

---

## 3. Route Structure

```
src/app/
├── layout.tsx                     # Root layout: dark theme, fonts, providers
├── page.tsx                       # Landing: ticker input → "Analyze" button
└── analysis/
    └── [ticker]/
        └── page.tsx               # Dashboard: pipeline vis + results
```

### 3.1 Landing Page (`page.tsx`)

Minimal. Center of screen:
- Company ticker input (with autocomplete/validation)
- "Analyze" button
- Dark background, subtle animated grid or particle background

On submit: `POST /api/analyze` → redirect to `/analysis/AAPL`

### 3.2 Analysis Dashboard (`analysis/[ticker]/page.tsx`)

Two states:
1. **Pipeline running:** Shows the pipeline visualization (4 layers as cards)
2. **Pipeline complete:** Transitions to results view (top 3 + other moves)

---

## 4. Pipeline Visualization

### 4.1 Overview Mode (Zoomed Out)

Four layer cards arranged horizontally (or vertically on mobile), connected by animated lines.

```
┌──────────┐     ┌──────────┐     ┌──────────┐     ┌──────────┐
│  Layer 0  │────▶│  Layer 1  │────▶│  Layer 2  │────▶│  Sandbox  │
│  Gather   │     │  Infer    │     │  Analyze  │     │  (L3+L4)  │
│           │     │           │     │           │     │           │
│  ● done   │     │  ◉ running│     │  ○ idle   │     │  ○ idle   │
└──────────┘     └──────────┘     └──────────┘     └──────────┘
```

Each card shows:
- Layer name
- Status indicator (idle / running / done)
- Progress ring or bar
- Number of agents (e.g., "2 agents" or "5 agents")
- Click to zoom in

### 4.2 Zoomed-In Mode

When a user clicks a layer card, it expands with an **ultra-smooth animated zoom transition** to fill the view. The other layers shrink and fade away.

Inside the zoomed view:
- Individual agent nodes with status (running spinner / checkmark)
- Output documents (F1, F2, m1–m15) as clickable cards
- For the sandbox: current policy being negotiated, round counter, live debate preview
- Close button (X) zooms back out with reverse animation

### 4.3 Zoom Animation Spec

```typescript
// Using Framer Motion's layoutId for shared element transitions
// + AnimatePresence for enter/exit

// LayerCard.tsx (overview mode)
<motion.div
  layoutId={`layer-${layerId}`}
  onClick={() => setZoomedLayer(layerId)}
  className="cursor-pointer"
  whileHover={{ scale: 1.02 }}
  transition={{ type: "spring", stiffness: 300, damping: 30 }}
>
  {/* Layer card content */}
</motion.div>

// LayerDetail.tsx (zoomed mode)
<motion.div
  layoutId={`layer-${layerId}`}
  className="fixed inset-4 z-50"
  transition={{ type: "spring", stiffness: 200, damping: 25 }}
>
  {/* Expanded layer detail content */}
  <motion.button
    onClick={() => setZoomedLayer(null)}
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ delay: 0.3 }}
  >
    ✕
  </motion.button>
</motion.div>
```

**Key animation parameters:**
- Transition type: `spring` (not `tween`) for natural feel
- Stiffness: 200–300 (responsive but not jarring)
- Damping: 25–30 (smooth deceleration, no bounce)
- Layout animations via Framer Motion's `layoutId` for seamless shared element transitions
- Backdrop blur overlay for other layers when one is zoomed

---

## 5. Component Breakdown

### 5.1 PipelineView

```typescript
// components/pipeline/PipelineView.tsx

interface PipelineViewProps {
  analysisId: string;
  ticker: string;
}

export function PipelineView({ analysisId, ticker }: PipelineViewProps) {
  const { events, status } = useSSE(analysisId);
  const { zoomedLayer, setZoomedLayer } = usePipelineZoom();
  const layers = useLayerStatus(events);

  return (
    <div className="relative w-full h-screen flex items-center justify-center">
      <AnimatePresence>
        {zoomedLayer === null ? (
          // Overview: 4 cards in a row
          <motion.div className="flex gap-8 items-center">
            {layers.map((layer, i) => (
              <Fragment key={layer.id}>
                {i > 0 && <ConnectionLine active={layer.status !== "idle"} />}
                <LayerCard
                  layer={layer}
                  onClick={() => setZoomedLayer(layer.id)}
                />
              </Fragment>
            ))}
          </motion.div>
        ) : (
          // Zoomed: full detail view
          <>
            <motion.div
              className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setZoomedLayer(null)}
            />
            <LayerDetail
              layer={layers.find(l => l.id === zoomedLayer)!}
              onClose={() => setZoomedLayer(null)}
            />
          </>
        )}
      </AnimatePresence>
    </div>
  );
}
```

### 5.2 LayerCard

```typescript
// components/pipeline/LayerCard.tsx

interface LayerCardProps {
  layer: LayerState;
  onClick: () => void;
}

export function LayerCard({ layer, onClick }: LayerCardProps) {
  return (
    <motion.div
      layoutId={`layer-${layer.id}`}
      onClick={onClick}
      className={cn(
        "w-48 h-64 rounded-2xl border cursor-pointer",
        "bg-zinc-900/80 backdrop-blur-xl",
        "border-zinc-700/50 hover:border-zinc-500/80",
        "flex flex-col items-center justify-center gap-4 p-6",
        "transition-colors duration-200",
        layer.status === "running" && "border-cyan-500/50 shadow-cyan-500/20 shadow-lg",
        layer.status === "done" && "border-emerald-500/30",
      )}
    >
      <StatusIndicator status={layer.status} />
      <h3 className="text-sm font-medium text-zinc-300">{layer.name}</h3>
      <p className="text-xs text-zinc-500">{layer.agentCount} agents</p>
      {layer.status === "running" && (
        <ProgressRing progress={layer.progress} />
      )}
    </motion.div>
  );
}
```

### 5.3 LayerDetail (Zoomed View)

```typescript
// components/pipeline/LayerDetail.tsx

export function LayerDetail({ layer, onClose }: LayerDetailProps) {
  return (
    <motion.div
      layoutId={`layer-${layer.id}`}
      className={cn(
        "fixed inset-6 z-50 rounded-3xl overflow-hidden",
        "bg-zinc-900/95 backdrop-blur-2xl border border-zinc-700/50",
        "flex flex-col"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between p-6 border-b border-zinc-800">
        <div>
          <h2 className="text-lg font-semibold text-white">{layer.name}</h2>
          <p className="text-sm text-zinc-400">{layer.description}</p>
        </div>
        <motion.button
          onClick={onClose}
          className="text-zinc-400 hover:text-white p-2"
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
        >
          <X className="w-5 h-5" />
        </motion.button>
      </div>

      {/* Agent grid */}
      <div className="flex-1 p-6 overflow-auto">
        <div className="grid grid-cols-3 gap-4">
          {layer.agents.map(agent => (
            <AgentNode key={agent.id} agent={agent} />
          ))}
        </div>

        {/* Output documents */}
        {layer.artifacts.length > 0 && (
          <div className="mt-8">
            <h3 className="text-sm font-medium text-zinc-400 mb-4">Output Documents</h3>
            <div className="grid grid-cols-2 gap-3">
              {layer.artifacts.map(artifact => (
                <DocumentViewer key={artifact.id} document={artifact} />
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
```

---

## 6. SSE Hook

```typescript
// hooks/useSSE.ts

import { useEffect, useState, useCallback } from "react";

interface SSEEvent {
  event: string;
  [key: string]: any;
}

export function useSSE(analysisId: string) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<"connecting" | "connected" | "done" | "error">("connecting");

  useEffect(() => {
    const source = new EventSource(`/api/stream/${analysisId}`);

    source.onopen = () => setStatus("connected");

    source.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      setEvents(prev => [...prev, event]);

      if (event.event === "pipeline_complete") {
        setStatus("done");
        source.close();
      }
      if (event.event === "pipeline_error") {
        setStatus("error");
        source.close();
      }
    };

    source.onerror = () => {
      setStatus("error");
      source.close();
    };

    return () => source.close();
  }, [analysisId]);

  return { events, status };
}
```

---

## 7. Zoom State Hook

```typescript
// hooks/usePipelineZoom.ts

import { useState, useCallback } from "react";

export function usePipelineZoom() {
  const [zoomedLayer, setZoomedLayer] = useState<string | null>(null);

  const zoomIn = useCallback((layerId: string) => {
    setZoomedLayer(layerId);
  }, []);

  const zoomOut = useCallback(() => {
    setZoomedLayer(null);
  }, []);

  return {
    zoomedLayer,
    setZoomedLayer,
    zoomIn,
    zoomOut,
    isZoomed: zoomedLayer !== null,
  };
}
```

---

## 8. Analysis State Hook

```typescript
// hooks/useAnalysis.ts

import { useMemo } from "react";

interface LayerState {
  id: string;
  name: string;
  description: string;
  status: "idle" | "running" | "done";
  agentCount: number;
  progress: number;
  agents: AgentState[];
  artifacts: ArtifactState[];
}

export function useLayerStatus(events: SSEEvent[]): LayerState[] {
  return useMemo(() => {
    const layers: LayerState[] = [
      { id: "layer_0", name: "Data Gathering", description: "Collecting financial and news data", status: "idle", agentCount: 0, progress: 0, agents: [], artifacts: [] },
      { id: "layer_1", name: "Inference", description: "Deriving insights from raw data", status: "idle", agentCount: 2, progress: 0, agents: [], artifacts: [] },
      { id: "layer_2", name: "Analysis", description: "Generating strategic moves", status: "idle", agentCount: 5, progress: 0, agents: [], artifacts: [] },
      { id: "sandbox", name: "Sandbox", description: "Debate & scoring (L3+L4)", status: "idle", agentCount: 4, progress: 0, agents: [], artifacts: [] },
    ];

    // Process events to update layer states
    for (const event of events) {
      if (event.event === "layer_start") {
        const layer = layers.find(l => l.id === `layer_${event.layer}` || l.id === event.layer);
        if (layer) layer.status = "running";
      }
      if (event.event === "layer_complete") {
        const layer = layers.find(l => l.id === `layer_${event.layer}` || l.id === event.layer);
        if (layer) {
          layer.status = "done";
          layer.progress = 100;
        }
      }
      if (event.event === "agent_complete") {
        const layer = layers.find(l => l.id === `layer_${event.layer}`);
        if (layer) {
          layer.agents.push({
            id: event.agent_id,
            status: "done",
            output: event.output,
          });
          layer.progress = (layer.agents.filter(a => a.status === "done").length / layer.agentCount) * 100;
        }
      }
      // ... handle sandbox_round, sandbox_scored, etc.
    }

    return layers;
  }, [events]);
}
```

---

## 9. Results View

After `pipeline_complete`, the dashboard transitions to the results view:

```typescript
// components/output/RecommendedMoves.tsx

export function RecommendedMoves({ moves }: { moves: MoveResult[] }) {
  return (
    <div className="space-y-6">
      <h2 className="text-xl font-semibold text-white">
        Recommended Moves
      </h2>
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {moves.map((move, i) => (
          <MoveCard
            key={move.move_id}
            move={move}
            rank={i + 1}
            variant="recommended"
          />
        ))}
      </div>
    </div>
  );
}
```

```typescript
// components/output/MoveCard.tsx

export function MoveCard({ move, rank, variant }: MoveCardProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      className={cn(
        "rounded-2xl border p-6",
        variant === "recommended"
          ? "bg-zinc-900 border-cyan-500/30"
          : "bg-zinc-900/50 border-zinc-800",
      )}
    >
      {/* Rank badge */}
      {variant === "recommended" && (
        <span className="text-xs font-bold text-cyan-400">#{rank}</span>
      )}

      {/* Score */}
      <div className="flex items-baseline gap-2 mt-2">
        <span className="text-3xl font-bold text-white">{move.total_score}</span>
        <span className="text-sm text-zinc-500">/120</span>
      </div>

      {/* Title */}
      <h3 className="text-sm font-medium text-zinc-200 mt-3">{move.move_document.title}</h3>
      <p className="text-xs text-zinc-500 mt-1">
        {move.move_document.persona} · {move.move_document.risk_level} risk
      </p>

      {/* Score breakdown */}
      <ScoreBreakdown scores={move.scores_by_agent} />

      {/* Expand for full reasoning */}
      <motion.button
        onClick={() => setExpanded(!expanded)}
        className="text-xs text-cyan-400 mt-4"
      >
        {expanded ? "Collapse" : "View reasoning & debate"}
      </motion.button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="mt-4 prose prose-invert prose-sm"
          >
            {/* Full markdown content + conversation logs */}
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
```

---

## 10. Color & Theme System

```css
/* styles/globals.css */

@tailwind base;
@tailwind components;
@tailwind utilities;

:root {
  --bg-primary: #09090b;        /* zinc-950 */
  --bg-card: #18181b;           /* zinc-900 */
  --border: #27272a;            /* zinc-800 */
  --text-primary: #fafafa;      /* zinc-50 */
  --text-secondary: #a1a1aa;    /* zinc-400 */
  --accent-cyan: #06b6d4;       /* cyan-500 */
  --accent-emerald: #10b981;    /* emerald-500 */
  --accent-amber: #f59e0b;      /* amber-500 */
}

body {
  background-color: var(--bg-primary);
  color: var(--text-primary);
}

/* Smooth transitions globally */
* {
  transition-timing-function: cubic-bezier(0.4, 0, 0.2, 1);
}
```

**Layer status colors:**
- Idle: `zinc-700` (muted)
- Running: `cyan-500` (glowing border + shadow)
- Done: `emerald-500` (subtle green checkmark)
- Error: `red-500`

---

## 11. Responsive Design

- **Desktop (>1024px):** 4 layer cards horizontal, results in 3-column grid
- **Tablet (768–1024px):** 2x2 grid for layers, results in 2-column grid
- **Mobile (<768px):** Vertical stack for layers, single-column results

Zoom-in transitions work on all viewports — the zoomed view takes `fixed inset-4` (small padding from edges on mobile) to `fixed inset-8` (more padding on desktop).
