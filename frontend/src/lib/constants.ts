/**
 * Constants — layer names, colors, animation durations.
 *
 * See: docs/architecture/LLD_frontend.md § 10
 */

export const LAYER_CONFIG = [
  {
    id: "layer0",
    name: "Data Gathering",
    description: "Synthesizing financial & news data",
    agentCount: 2,
    color: "blue",
  },
  {
    id: "layer1",
    name: "Inference",
    description: "Deriving insights from raw data",
    agentCount: 2,
    color: "cyan",
  },
  {
    id: "layer2",
    name: "Analysis",
    description: "Generating strategic moves",
    agentCount: 5,
    color: "cyan",
  },
  {
    id: "layer3",
    name: "Sandbox",
    description: "Negotiation & scoring of strategic moves",
    agentCount: 3,
    color: "purple",
  },
] as const;

export const STATUS_COLORS = {
  idle: "zinc-700",
  running: "cyan-500",
  done: "emerald-500",
  error: "red-500",
} as const;

export const ANIMATION = {
  // Spring transition for zoom (Framer Motion)
  zoomSpring: {
    type: "spring" as const,
    stiffness: 200,
    damping: 25,
  },
  // Hover scale
  hoverScale: 1.02,
  // Backdrop fade duration
  backdropDuration: 0.2,
} as const;

export const SCORING_METRICS = [
  { key: "impact", label: "Impact", color: "#06b6d4" },
  { key: "feasibility", label: "Feasibility", color: "#10b981" },
  { key: "risk_adjusted_return", label: "Risk-Adj Return", color: "#f59e0b" },
  { key: "strategic_alignment", label: "Strategic Fit", color: "#8b5cf6" },
] as const;
