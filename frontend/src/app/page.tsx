/**
 * Landing page — ticker input -> "Analyze" button.
 * See: docs/architecture/LLD_frontend.md § 3.1
 */

import { TickerInput } from "@/components/input/TickerInput";

export default function Home() {
  return (
    <main className="flex min-h-screen items-center justify-center relative overflow-hidden">
      {/* Ambient background glow */}
      <div className="absolute top-1/3 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[400px] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none" />

      <div className="relative z-10 text-center">
        <div className="mb-3">
          <span className="text-xs font-mono uppercase tracking-[0.3em] text-white/30 bg-white/[0.04] px-4 py-1.5 rounded-full border border-white/[0.06]">
            Multi-Agent Pipeline
          </span>
        </div>
        <h1 className="text-5xl font-bold mb-4 tracking-tight bg-gradient-to-b from-white to-white/60 bg-clip-text text-transparent">
          AI Consulting Agency
        </h1>
        <p className="text-white/40 mb-12 text-lg">
          Enter a company ticker to begin strategic analysis
        </p>
        <TickerInput />
      </div>
    </main>
  );
}
