/**
 * Analysis dashboard — pipeline visualization + results.
 * See: docs/architecture/LLD_frontend.md § 3.2
 */

"use client";

import { useEffect, useState } from "react";
import { useSearchParams, useParams } from "next/navigation";
import { PipelineView } from "@/components/pipeline/PipelineView";
import { startAnalysis } from "@/lib/api";

export default function AnalysisPage() {
  const params = useParams<{ ticker: string }>();
  const searchParams = useSearchParams();
  const ticker = params.ticker;

  const [analysisId, setAnalysisId] = useState<string | null>(
    searchParams.get("id")
  );
  const [error, setError] = useState("");

  // If no analysis_id in URL, start a new analysis
  useEffect(() => {
    if (analysisId) return;

    let cancelled = false;
    startAnalysis(ticker)
      .then((data) => {
        if (!cancelled) {
          setAnalysisId(data.analysis_id);
          // Update URL without navigation
          window.history.replaceState(
            null,
            "",
            `/analysis/${ticker}?id=${data.analysis_id}`
          );
        }
      })
      .catch((err) => {
        if (!cancelled) setError(err.message || "Failed to start analysis");
      });

    return () => {
      cancelled = true;
    };
  }, [analysisId, ticker]);

  return (
    <main className="min-h-screen bg-[#02040a] text-white overflow-hidden relative selection:bg-blue-500/30">
      {/* Top Bar with Ticker */}
      <div className="absolute top-0 left-0 right-0 z-50 px-8 py-6 flex items-center justify-between pointer-events-none">
        <div className="flex items-center gap-4 pointer-events-auto">
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center font-bold text-white tracking-widest">
            {ticker.slice(0, 2).toUpperCase()}
          </div>
          <div>
            <h1 className="text-lg font-bold tracking-tight text-white">
              {ticker.toUpperCase()}
            </h1>
            <p className="text-xs text-white/40 font-medium">
              Strategic Analysis Pipeline
            </p>
          </div>
        </div>
      </div>

      {error ? (
        <div className="flex items-center justify-center h-screen">
          <p className="text-red-400">{error}</p>
        </div>
      ) : !analysisId ? (
        <div className="flex items-center justify-center h-screen">
          <p className="text-white/40 animate-pulse">
            Starting analysis...
          </p>
        </div>
      ) : (
        <PipelineView analysisId={analysisId} ticker={ticker} />
      )}
    </main>
  );
}
