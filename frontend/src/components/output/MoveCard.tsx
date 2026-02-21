"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, Trophy, TrendingUp, Shield, Zap } from "lucide-react";
import { type MoveResult } from "@/lib/types";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";
import { cn } from "@/lib/utils";

const RISK_STYLES: Record<string, { bg: string; text: string; border: string }> = {
  low: { bg: "bg-emerald-500/10", text: "text-emerald-400", border: "border-emerald-500/20" },
  medium: { bg: "bg-amber-500/10", text: "text-amber-400", border: "border-amber-500/20" },
  high: { bg: "bg-red-500/10", text: "text-red-400", border: "border-red-500/20" },
};

const RANK_ICONS = [Trophy, TrendingUp, Shield];

function scoreColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 70) return "text-sky-400";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
}

function scoreBorderColor(score: number): string {
  if (score >= 90) return "border-emerald-500/30 shadow-[0_0_15px_-5px_rgba(16,185,129,0.3)]";
  if (score >= 70) return "border-sky-500/30 shadow-[0_0_15px_-5px_rgba(56,189,248,0.3)]";
  if (score >= 50) return "border-amber-500/30 shadow-[0_0_15px_-5px_rgba(245,158,11,0.3)]";
  return "border-white/[0.08]";
}

interface MoveCardProps {
  move: MoveResult;
  rank: number;
  highlighted?: boolean;
}

export function MoveCard({ move, rank, highlighted = true }: MoveCardProps) {
  const [expanded, setExpanded] = useState(false);

  const risk = move.move_document?.risk_level ?? "medium";
  const riskStyle = RISK_STYLES[risk] ?? RISK_STYLES.medium;
  const RankIcon = rank <= 3 ? RANK_ICONS[rank - 1] ?? Zap : Zap;
  const score = move.total_score ?? 0;

  return (
    <motion.div
      layout
      className={cn(
        "rounded-2xl border overflow-hidden transition-all duration-300",
        highlighted
          ? `bg-white/[0.03] backdrop-blur-sm ${scoreBorderColor(score)}`
          : "bg-white/[0.015] border-white/[0.06] opacity-60 hover:opacity-80"
      )}
    >
      {/* Header */}
      <div className="p-5">
        <div className="flex items-start justify-between gap-3 mb-3">
          <div className="flex items-center gap-2.5">
            {highlighted && rank <= 3 && (
              <div className={cn(
                "w-8 h-8 rounded-lg flex items-center justify-center",
                rank === 1 ? "bg-amber-500/20 text-amber-400" :
                rank === 2 ? "bg-slate-400/20 text-slate-300" :
                "bg-orange-500/20 text-orange-400"
              )}>
                <RankIcon className="w-4 h-4" />
              </div>
            )}
            <div>
              <span className="text-[10px] font-mono font-bold text-white/40 uppercase tracking-wider">
                #{rank} — {move.move_id?.toUpperCase()}
              </span>
              <h3 className={cn(
                "text-sm font-semibold leading-tight mt-0.5",
                highlighted ? "text-white/90" : "text-white/50"
              )}>
                {move.move_document?.title ?? "Untitled Move"}
              </h3>
            </div>
          </div>

          {/* Score badge */}
          <div className="flex flex-col items-end flex-shrink-0">
            <span className={cn("text-xl font-bold tabular-nums", scoreColor(score))}>
              {score}
            </span>
            <span className="text-[10px] text-white/30 font-mono">/120</span>
          </div>
        </div>

        {/* Meta tags */}
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cn(
            "text-[10px] px-2 py-0.5 rounded-full font-mono border",
            riskStyle.bg, riskStyle.text, riskStyle.border
          )}>
            {risk} risk
          </span>
          {move.move_document?.persona && (
            <span className="text-[10px] px-2 py-0.5 rounded-full font-mono bg-white/5 text-white/40 border border-white/[0.06]">
              {move.move_document.persona}
            </span>
          )}
        </div>

        {/* Radar chart */}
        {highlighted && move.scores_by_agent && Object.keys(move.scores_by_agent).length > 0 && (
          <div className="mt-4">
            <ScoreBreakdown scoresByAgent={move.scores_by_agent} />
          </div>
        )}
      </div>

      {/* Expand toggle */}
      <div
        onClick={() => setExpanded(!expanded)}
        className={cn(
          "flex items-center justify-center gap-2 px-5 py-2.5 cursor-pointer border-t transition-colors",
          expanded
            ? "bg-white/[0.04] border-white/[0.08] text-white/50"
            : "bg-white/[0.02] border-white/[0.04] text-white/25 hover:text-white/40 hover:bg-white/[0.03]"
        )}
      >
        <span className="text-[10px] font-mono uppercase tracking-wider">
          {expanded ? "Hide Details" : "View Move Content"}
        </span>
        <motion.div animate={{ rotate: expanded ? 180 : 0 }}>
          <ChevronDown className="w-3.5 h-3.5" />
        </motion.div>
      </div>

      {/* Expandable content */}
      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25 }}
            className="border-t border-white/[0.05]"
          >
            <div className="p-5 bg-black/20 max-h-[400px] overflow-y-auto custom-scrollbar">
              <MarkdownRenderer
                content={move.move_document?.content ?? "No content available."}
                compact
              />
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
