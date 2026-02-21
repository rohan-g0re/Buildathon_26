/**
 * API client — POST /analyze, GET /results/:id
 *
 * See: docs/architecture/LLD_pipeline.md § 5
 */

const API_BASE = process.env.NEXT_PUBLIC_API_URL || "";

// Direct backend URL — used for long-lived or CORS-sensitive requests
// that shouldn't go through the Next.js rewrite proxy.
const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";

export async function startAnalysis(ticker: string) {
  const res = await fetch(`${API_BASE}/api/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ticker }),
  });
  if (!res.ok) throw new Error(`Failed to start analysis: ${res.statusText}`);
  return res.json();
}

export async function getResults(analysisId: string) {
  const res = await fetch(`${BACKEND_URL}/api/results/${analysisId}`);
  if (!res.ok) throw new Error(`Failed to get results: ${res.statusText}`);
  return res.json();
}
