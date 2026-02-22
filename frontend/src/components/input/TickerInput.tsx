/**
 * TickerInput — Company ticker input with "Analyze" button.
 * On submit: POST /api/analyze -> redirect to /analysis/[ticker]?id=...
 *
 * See: docs/architecture/LLD_frontend.md § 3.1
 */

"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { startAnalysis } from "@/lib/api";

export function TickerInput() {
  const [ticker, setTicker] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const router = useRouter();

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    const cleaned = ticker.trim().toUpperCase();
    if (!cleaned || !/^[A-Z]{1,5}$/.test(cleaned)) {
      setError("Enter a valid ticker (1-5 letters)");
      return;
    }

    setError("");
    setLoading(true);

    try {
      const data = await startAnalysis(cleaned);
      router.push(`/analysis/${cleaned}?id=${data.analysis_id}`);
    } catch (err: any) {
      setError(err.message || "Failed to start analysis");
      setLoading(false);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="flex flex-col items-center gap-4">
      <div className="flex gap-3">
        <input
          type="text"
          value={ticker}
          onChange={(e) => {
            setTicker(e.target.value.toUpperCase());
            setError("");
          }}
          placeholder="Enter ticker"
          disabled={loading}
          className="px-5 py-3 rounded-xl bg-white/[0.04] border border-white/10 text-white placeholder-white/30 focus:outline-none focus:border-blue-500/50 focus:ring-1 focus:ring-blue-500/30 w-64 font-mono tracking-wider text-left text-lg transition-all disabled:opacity-50"
          maxLength={5}
          autoFocus
        />
        <button
          type="submit"
          disabled={loading || !ticker.trim()}
          className="px-8 py-3 rounded-xl bg-blue-600 hover:bg-blue-500 text-white font-semibold transition-all disabled:opacity-40 disabled:cursor-not-allowed shadow-lg shadow-blue-500/20 hover:shadow-blue-500/40"
        >
          {loading ? (
            <span className="flex items-center gap-2">
              <svg className="animate-spin h-4 w-4" viewBox="0 0 24 24">
                <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" fill="none" />
                <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
              </svg>
              Starting...
            </span>
          ) : (
            "Analyze"
          )}
        </button>
      </div>
      {error && (
        <p className="text-red-400 text-sm">{error}</p>
      )}
    </form>
  );
}
