/**
 * PipelineView — Top-level: 4 layer cards in a row with zoom transitions.
 *
 * Overview mode: 4 LayerCards connected by ConnectionLines.
 * Zoomed mode: One LayerDetail fills the view, others fade.
 * Global progress bar at top shows overall pipeline completion.
 * Completion summary appears when all layers finish.
 *
 * See: docs/architecture/LLD_frontend.md § 5.1
 */

"use client";

import { Fragment, useEffect, useMemo, useRef, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { useSSE } from "@/hooks/useSSE";
import { usePipelineZoom } from "@/hooks/usePipelineZoom";
import { useLayerStatus, type LayerState, type ArtifactState } from "@/hooks/useLayerStatus";
import { getResults } from "@/lib/api";
import { LayerCard } from "./LayerCard";
import { LayerDetail } from "./LayerDetail";
import { ConnectionLine } from "./ConnectionLine";
import { CheckCircle2 } from "lucide-react";

interface PipelineViewProps {
  analysisId: string;
  ticker: string;
}

export function PipelineView({ analysisId, ticker }: PipelineViewProps) {
  const { events, status } = useSSE(analysisId);
  const { zoomedLayer, setZoomedLayer, isZoomed } = usePipelineZoom();
  const layers = useLayerStatus(events);

  // ---------- Fetch partial results as each layer completes ----------
  const [results, setResults] = useState<Record<string, unknown> | null>(null);

  // Count how many layer_complete events have been received so far.
  const completedLayerCount = useMemo(() => {
    return events.filter((e) => e.event === "layer_complete").length;
  }, [events]);

  // Track the last count we fetched for so we don't re-fetch unnecessarily.
  const lastFetchedCount = useRef(0);

  useEffect(() => {
    if (completedLayerCount > lastFetchedCount.current && analysisId) {
      lastFetchedCount.current = completedLayerCount;
      getResults(analysisId)
        .then((data) => setResults(data.result ?? data))
        .catch((err) => console.error("Failed to fetch results:", err));
    }
  }, [completedLayerCount, analysisId]);

  // ---------- Enrich layers with artifacts from results ----------
  const enrichedLayers: LayerState[] = useMemo(() => {
    if (!results) return layers;

    return layers.map((layer) => {
      const artifacts: ArtifactState[] = [...layer.artifacts];

      if (layer.id === "layer0") {
        // Layer 0 — raw data documents
        const fin = results.financial_data_raw as string | undefined;
        const news = results.news_data_raw as string | undefined;
        if (fin) artifacts.push({ id: "financial_data_raw", title: "Financial Data (Raw)", type: "data", content: fin });
        if (news) artifacts.push({ id: "news_data_raw", title: "News Data (Raw)", type: "data", content: news });
      }

      if (layer.id === "layer1") {
        // Layer 1 — inference reports
        const f1 = results.f1 as string | undefined;
        const f2 = results.f2 as string | undefined;
        if (f1) artifacts.push({ id: "f1", title: "Financial Inference (F1)", type: "report", content: f1 });
        if (f2) artifacts.push({ id: "f2", title: "Trend Inference (F2)", type: "report", content: f2 });
      }

      if (layer.id === "layer2") {
        // Layer 2 — move suggestions
        const moves = results.move_suggestions as Array<Record<string, unknown>> | undefined;
        if (moves && moves.length > 0) {
          for (const move of moves) {
            const moveId = (move.move_id as string) || `move-${artifacts.length}`;
            const title = (move.title as string) || moveId;
            const persona = (move.persona as string) || "";
            const risk = (move.risk_level as string) || "";
            const body = (move.content as string) || JSON.stringify(move, null, 2);
            const header = [persona && `Persona: ${persona}`, risk && `Risk: ${risk}`].filter(Boolean).join(" | ");
            artifacts.push({
              id: moveId,
              title,
              type: "move",
              content: header ? `${header}\n\n${body}` : body,
            });
          }
        }
      }

      if (layer.id === "layer3") {
        // Layer 3 (Sandbox) — recommended moves with scores + conversation logs
        const recommended = results.recommended_moves as Array<Record<string, unknown>> | undefined;
        const other = results.other_moves as Array<Record<string, unknown>> | undefined;

        if (recommended && recommended.length > 0) {
          for (const entry of recommended) {
            const moveId = (entry.move_id as string) || "?";
            const score = (entry.total_score as number) ?? 0;
            const moveDoc = entry.move_document as Record<string, unknown> | undefined;
            const title = (moveDoc?.title as string) || moveId;
            const scoresBy = entry.scores_by_agent as Record<string, Record<string, unknown>> | undefined;
            let body = `**Score: ${score}/120** | **Recommended**\n\n`;
            if (scoresBy) {
              for (const [dmId, dmScores] of Object.entries(scoresBy)) {
                const subtotal = Object.entries(dmScores)
                  .filter(([k]) => k !== "reasoning")
                  .reduce((sum, [, v]) => sum + (typeof v === "number" ? v : 0), 0);
                body += `### ${dmId} (${subtotal}/40)\n`;
                for (const [metric, val] of Object.entries(dmScores)) {
                  if (metric !== "reasoning") body += `- ${metric}: ${val}/10\n`;
                }
                if (dmScores.reasoning) body += `\n*${dmScores.reasoning}*\n\n`;
              }
            }
            artifacts.push({ id: `rec-${moveId}`, title: `${moveId}: ${title}`, type: "recommended", content: body });
          }
        }

        if (other && other.length > 0) {
          for (const entry of other) {
            const moveId = (entry.move_id as string) || "?";
            const score = (entry.total_score as number) ?? 0;
            const moveDoc = entry.move_document as Record<string, unknown> | undefined;
            const title = (moveDoc?.title as string) || moveId;
            const skipped = entry.skipped as boolean | undefined;
            artifacts.push({
              id: `other-${moveId}`,
              title: `${moveId}: ${title}${skipped ? " (Skipped)" : ""}`,
              type: "scored",
              content: `**Score: ${score}/120**${skipped ? " | Skipped" : ""}`,
            });
          }
        }

        // Conversation logs (single shared thread per move)
        const convLogs = results.conversation_logs as Array<Record<string, unknown>> | undefined;
        if (convLogs && convLogs.length > 0) {
          for (const log of convLogs) {
            const moveId = (log.move_id as string) || "?";
            const conversation = log.conversation as Array<Record<string, unknown>> | undefined;
            let transcript = `# Negotiation: ${moveId}\n\n`;
            if (conversation && conversation.length > 0) {
              for (const entry of conversation) {
                const roleLabel = entry.role === "critic"
                  ? "CRITIC"
                  : `DECISION MAKER (${entry.role})`;
                transcript += `**[Round ${entry.round}] ${roleLabel}:**\n${entry.content}\n\n---\n\n`;
              }
            }
            artifacts.push({ id: `conv-${moveId}`, title: `Negotiation: ${moveId}`, type: "conversation", content: transcript });
          }
        }
      }

      return { ...layer, artifacts };
    });
  }, [layers, results]);

  // Compute overall progress (each layer = 33.3%)
  const overallProgress = useMemo(() => {
    const doneCount = enrichedLayers.filter((l) => l.status === "done").length;
    const runningLayer = enrichedLayers.find((l) => l.status === "running");
    const runningContribution = runningLayer
      ? (runningLayer.progress / 100) * (100 / enrichedLayers.length)
      : 0;
    return Math.round((doneCount / enrichedLayers.length) * 100 + runningContribution);
  }, [enrichedLayers]);

  const isPipelineDone = status === "done";
  const isPipelineError = status === "error";

  // Count total moves from events
  const totalMoves = useMemo(() => {
    let count = 0;
    for (const e of events) {
      if (e.event === "layer_complete" && e.layer === 2 && e.total_moves) {
        count = e.total_moves;
      }
    }
    return count;
  }, [events]);

  return (
    <div className="relative w-full h-[calc(100vh-100px)] flex flex-col items-center justify-center overflow-hidden">
      {/* Global Progress Bar — fixed at top */}
      <div className="absolute top-24 left-0 right-0 z-30 px-8">
        <div className="max-w-3xl mx-auto">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-mono text-white/40 uppercase tracking-wider">
              Pipeline Progress
            </span>
            <span className="text-xs font-mono text-white/60">
              {overallProgress}%
            </span>
          </div>
          <div className="h-1 w-full bg-white/[0.06] rounded-full overflow-hidden">
            <motion.div
              className={`h-full rounded-full ${
                isPipelineError
                  ? "bg-red-500"
                  : isPipelineDone
                  ? "bg-emerald-500"
                  : "bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.6)]"
              }`}
              initial={{ width: 0 }}
              animate={{ width: `${overallProgress}%` }}
              transition={{ type: "spring", stiffness: 50, damping: 20 }}
            />
          </div>
          {/* Layer completion indicators */}
          <div className="flex justify-between mt-2">
            {enrichedLayers.map((layer) => (
              <div key={layer.id} className="flex items-center gap-1.5">
                <div
                  className={`w-1.5 h-1.5 rounded-full transition-colors duration-300 ${
                    layer.status === "done"
                      ? "bg-emerald-500"
                      : layer.status === "running"
                      ? "bg-blue-500 animate-pulse"
                      : layer.status === "error"
                      ? "bg-red-500"
                      : "bg-white/10"
                  }`}
                />
                <span
                  className={`text-[10px] font-medium transition-colors duration-300 ${
                    layer.status === "done"
                      ? "text-emerald-400/80"
                      : layer.status === "running"
                      ? "text-blue-400/80"
                      : "text-white/20"
                  }`}
                >
                  {layer.name}
                </span>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Ambient Background Glow */}
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[800px] h-[500px] bg-blue-500/10 blur-[120px] rounded-full pointer-events-none" />

      <AnimatePresence mode="wait">
        {isPipelineDone && !isZoomed ? (
          // Completion Summary
          <motion.div
            key="complete"
            className="relative z-10 flex flex-col items-center gap-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            transition={{ duration: 0.5 }}
          >
            {/* Success badge */}
            <motion.div
              className="flex items-center gap-3 bg-emerald-500/10 border border-emerald-500/20 px-6 py-3 rounded-2xl"
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
              transition={{ delay: 0.2, type: "spring", stiffness: 200 }}
            >
              <CheckCircle2 className="w-5 h-5 text-emerald-400" />
              <span className="text-emerald-300 font-semibold text-sm">
                Analysis Complete
              </span>
            </motion.div>

            <div className="text-center">
              <h2 className="text-3xl font-bold text-white mb-2">
                {ticker.toUpperCase()} Analysis
              </h2>
              <p className="text-white/40">
                {totalMoves > 0
                  ? `${totalMoves} strategic moves generated and scored across 4 layers`
                  : "All layers completed successfully"}
              </p>
            </div>

            {/* Layer cards — clickable to view details */}
            <div className="flex gap-4 items-center">
              {enrichedLayers.map((layer, i) => (
                <Fragment key={layer.id}>
                  {i > 0 && <ConnectionLine active={false} />}
                  <LayerCard
                    layer={layer}
                    index={i}
                    onClick={() => setZoomedLayer(layer.id)}
                  />
                </Fragment>
              ))}
            </div>
          </motion.div>
        ) : !isZoomed ? (
          // Overview: 4 cards in a row
          <motion.div
            key="overview"
            className="relative z-10 flex gap-5 items-center px-8 py-12 overflow-x-auto max-w-full justify-center hide-scrollbar"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{
              opacity: 0,
              scale: 0.95,
              filter: "blur(10px)",
              transition: { duration: 0.3 },
            }}
          >
            {enrichedLayers.map((layer, i) => (
              <Fragment key={layer.id}>
                {i > 0 && (
                  <ConnectionLine
                    active={
                      layer.status === "running" || layer.status === "done"
                    }
                  />
                )}
                <LayerCard
                  layer={layer}
                  index={i}
                  onClick={() => setZoomedLayer(layer.id)}
                />
              </Fragment>
            ))}
          </motion.div>
        ) : (
          // Zoomed: full detail view
          <Fragment key="zoomed">
            <motion.div
              className="fixed inset-0 bg-[#02040a]/80 backdrop-blur-md z-40 transition-opacity duration-500"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setZoomedLayer(null)}
            />
            <LayerDetail
              layer={enrichedLayers.find((l) => l.id === zoomedLayer)!}
              onClose={() => setZoomedLayer(null)}
              events={events}
            />
          </Fragment>
        )}
      </AnimatePresence>

      {/* Error banner */}
      {isPipelineError && (
        <motion.div
          className="absolute bottom-8 left-1/2 -translate-x-1/2 z-30 bg-red-500/10 border border-red-500/30 px-6 py-3 rounded-xl"
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
        >
          <p className="text-red-400 text-sm">
            Pipeline encountered an error. Check the console for details.
          </p>
        </motion.div>
      )}
    </div>
  );
}
