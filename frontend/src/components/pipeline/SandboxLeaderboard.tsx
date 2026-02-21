"use client";

import { useMemo, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Trophy,
  ChevronUp,
  ChevronDown,
  Minus,
  Loader2,
  XCircle,
  Clock,
} from "lucide-react";
import { type SSEEvent } from "@/hooks/useSSE";
import { cn } from "@/lib/utils";

interface LeaderboardEntry {
  moveId: string;
  title: string;
  riskLevel: string;
  persona: string;
  status: "negotiating" | "scored" | "skipped";
  currentRound: number;
  maxRounds: number;
  score: number | null;
  breakdown: Record<string, Record<string, number>> | null;
}

interface SandboxLeaderboardProps {
  events: SSEEvent[];
  selectedMoveId: string | null;
  onSelectMove: (moveId: string) => void;
}

const RISK_COLORS: Record<string, { bg: string; text: string }> = {
  low: { bg: "bg-emerald-500/15", text: "text-emerald-400" },
  medium: { bg: "bg-amber-500/15", text: "text-amber-400" },
  high: { bg: "bg-red-500/15", text: "text-red-400" },
};

function scoreColor(score: number): string {
  if (score >= 90) return "text-emerald-400";
  if (score >= 70) return "text-sky-400";
  if (score >= 50) return "text-amber-400";
  return "text-red-400";
}

function barGradient(score: number): string {
  if (score >= 90) return "from-emerald-500 to-emerald-400";
  if (score >= 70) return "from-sky-500 to-sky-400";
  if (score >= 50) return "from-amber-500 to-amber-400";
  return "from-red-500 to-red-400";
}

export function SandboxLeaderboard({
  events,
  selectedMoveId,
  onSelectMove,
}: SandboxLeaderboardProps) {
  const listRef = useRef<HTMLDivElement>(null);

  const entries = useMemo(() => {
    const map = new Map<string, LeaderboardEntry>();

    for (const event of events) {
      const moveId = event.move as string | undefined;
      if (!moveId) continue;

      switch (event.event) {
        case "sandbox_move_start": {
          if (!map.has(moveId)) {
            map.set(moveId, {
              moveId,
              title: (event.title as string) || moveId,
              riskLevel: (event.risk_level as string) || "unknown",
              persona: (event.persona as string) || "",
              status: "negotiating",
              currentRound: 0,
              maxRounds: (event.max_rounds as number) || 3,
              score: null,
              breakdown: null,
            });
          }
          break;
        }
        case "sandbox_round": {
          const existing = map.get(moveId);
          if (existing) {
            const round = event.round as number;
            if (round > existing.currentRound) {
              existing.currentRound = round;
            }
          }
          break;
        }
        case "sandbox_scored": {
          const existing = map.get(moveId);
          if (existing) {
            existing.status = "scored";
            existing.score = event.score as number;
            existing.breakdown =
              (event.breakdown as Record<string, Record<string, number>>) ||
              null;
            if (event.title) existing.title = event.title as string;
          } else {
            map.set(moveId, {
              moveId,
              title: (event.title as string) || moveId,
              riskLevel: "unknown",
              persona: "",
              status: "scored",
              currentRound: 0,
              maxRounds: 3,
              score: event.score as number,
              breakdown:
                (event.breakdown as Record<string, Record<string, number>>) ||
                null,
            });
          }
          break;
        }
        case "sandbox_skipped": {
          const existing = map.get(moveId);
          if (existing) {
            existing.status = "skipped";
          } else {
            map.set(moveId, {
              moveId,
              title: moveId,
              riskLevel: "unknown",
              persona: "",
              status: "skipped",
              currentRound: 0,
              maxRounds: 3,
              score: null,
              breakdown: null,
            });
          }
          break;
        }
      }
    }

    return Array.from(map.values());
  }, [events]);

  const previousPositions = useRef<Map<string, number>>(new Map());

  const sorted = useMemo(() => {
    const scored = entries
      .filter((e) => e.status === "scored")
      .sort((a, b) => (b.score ?? 0) - (a.score ?? 0));
    const negotiating = entries
      .filter((e) => e.status === "negotiating")
      .sort((a, b) => b.currentRound - a.currentRound);
    const skipped = entries.filter((e) => e.status === "skipped");

    return [...scored, ...negotiating, ...skipped];
  }, [entries]);

  const positionDeltas = useMemo(() => {
    const deltas = new Map<string, number>();
    const prev = previousPositions.current;

    sorted.forEach((entry, idx) => {
      const prevPos = prev.get(entry.moveId);
      if (prevPos !== undefined) {
        deltas.set(entry.moveId, prevPos - idx);
      }
    });

    const next = new Map<string, number>();
    sorted.forEach((entry, idx) => next.set(entry.moveId, idx));
    previousPositions.current = next;

    return deltas;
  }, [sorted]);

  useEffect(() => {
    if (listRef.current) {
      const selected = listRef.current.querySelector(
        '[data-selected="true"]'
      );
      if (selected) {
        selected.scrollIntoView({ behavior: "smooth", block: "nearest" });
      }
    }
  }, [selectedMoveId]);

  if (sorted.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-3 text-white/20">
        <Clock className="w-8 h-8 opacity-50" />
        <p className="text-xs font-mono">Waiting for moves...</p>
      </div>
    );
  }

  const scoredCount = sorted.filter((e) => e.status === "scored").length;

  return (
    <div className="flex flex-col h-full gap-3">
      {/* Header */}
      <div className="flex items-center justify-between px-1">
        <div className="flex items-center gap-2">
          <Trophy className="w-4 h-4 text-amber-400" />
          <span className="text-xs font-bold text-white/60 uppercase tracking-widest">
            Leaderboard
          </span>
        </div>
        <span className="text-[10px] font-mono text-white/30">
          {scoredCount}/{sorted.length} scored
        </span>
      </div>

      {/* Leaderboard rows */}
      <div
        ref={listRef}
        className="flex-1 overflow-y-auto custom-scrollbar space-y-1.5 pr-1 min-h-0"
      >
        <AnimatePresence mode="popLayout">
          {sorted.map((entry, idx) => {
            const position = idx + 1;
            const delta = positionDeltas.get(entry.moveId) ?? 0;
            const isSelected = selectedMoveId === entry.moveId;
            const risk = RISK_COLORS[entry.riskLevel] || RISK_COLORS.medium;

            return (
              <motion.div
                key={entry.moveId}
                layout
                initial={{ opacity: 0, scale: 0.95 }}
                animate={{ opacity: 1, scale: 1 }}
                exit={{ opacity: 0, scale: 0.95 }}
                transition={{
                  layout: { type: "spring", stiffness: 400, damping: 30 },
                  opacity: { duration: 0.2 },
                }}
                data-selected={isSelected}
                onClick={() => onSelectMove(entry.moveId)}
                className={cn(
                  "group relative flex items-center gap-2 px-2.5 py-2 rounded-xl cursor-pointer transition-colors duration-150",
                  "border",
                  isSelected
                    ? "bg-white/[0.08] border-purple-500/40"
                    : "bg-white/[0.02] border-white/[0.06] hover:bg-white/[0.05] hover:border-white/[0.12]",
                  entry.status === "negotiating" && "animate-pulse-subtle"
                )}
              >
                {/* Position */}
                <div className="flex flex-col items-center w-7 flex-shrink-0">
                  <span
                    className={cn(
                      "text-sm font-bold tabular-nums",
                      position <= 3 && entry.status === "scored"
                        ? "text-amber-400"
                        : "text-white/40"
                    )}
                  >
                    {entry.status === "scored" ? position : "--"}
                  </span>
                  {delta !== 0 && entry.status === "scored" && (
                    <motion.span
                      initial={{ opacity: 0, y: delta > 0 ? 4 : -4 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={cn(
                        "text-[9px] font-bold flex items-center leading-none",
                        delta > 0 ? "text-emerald-400" : "text-red-400"
                      )}
                    >
                      {delta > 0 ? (
                        <ChevronUp className="w-2.5 h-2.5" />
                      ) : (
                        <ChevronDown className="w-2.5 h-2.5" />
                      )}
                      {Math.abs(delta)}
                    </motion.span>
                  )}
                  {delta === 0 &&
                    entry.status === "scored" &&
                    sorted.filter((e) => e.status === "scored").length > 1 && (
                      <Minus className="w-2.5 h-2.5 text-white/15" />
                    )}
                </div>

                {/* Colored left edge */}
                <div
                  className={cn(
                    "w-0.5 h-8 rounded-full flex-shrink-0",
                    entry.status === "scored"
                      ? entry.score! >= 90
                        ? "bg-emerald-500"
                        : entry.score! >= 70
                          ? "bg-sky-500"
                          : entry.score! >= 50
                            ? "bg-amber-500"
                            : "bg-red-500"
                      : entry.status === "negotiating"
                        ? "bg-purple-500/60"
                        : "bg-white/10"
                  )}
                />

                {/* Move info */}
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-1.5">
                    <span className="text-[10px] font-mono font-bold text-white/50 flex-shrink-0">
                      {entry.moveId.toUpperCase()}
                    </span>
                    <span
                      className={cn(
                        "text-[9px] px-1.5 py-0.5 rounded-full font-mono flex-shrink-0",
                        risk.bg,
                        risk.text
                      )}
                    >
                      {entry.riskLevel}
                    </span>
                  </div>
                  <p className="text-xs text-white/60 truncate mt-0.5 leading-tight">
                    {entry.title}
                  </p>
                </div>

                {/* Status / Score */}
                <div className="flex flex-col items-end flex-shrink-0 gap-0.5">
                  {entry.status === "scored" && entry.score !== null && (
                    <>
                      <span
                        className={cn(
                          "text-sm font-bold tabular-nums",
                          scoreColor(entry.score)
                        )}
                      >
                        {entry.score}
                      </span>
                      <div className="w-14 h-1.5 rounded-full bg-white/[0.06] overflow-hidden">
                        <motion.div
                          className={cn(
                            "h-full rounded-full bg-gradient-to-r",
                            barGradient(entry.score)
                          )}
                          initial={{ width: 0 }}
                          animate={{
                            width: `${(entry.score / 120) * 100}%`,
                          }}
                          transition={{ duration: 0.6, ease: "easeOut" }}
                        />
                      </div>
                    </>
                  )}
                  {entry.status === "negotiating" && (
                    <div className="flex items-center gap-1.5">
                      <span className="text-[10px] font-mono text-purple-400/70">
                        R{entry.currentRound}/{entry.maxRounds}
                      </span>
                      <Loader2 className="w-3 h-3 text-purple-400 animate-spin" />
                    </div>
                  )}
                  {entry.status === "skipped" && (
                    <XCircle className="w-3.5 h-3.5 text-white/20" />
                  )}
                </div>
              </motion.div>
            );
          })}
        </AnimatePresence>
      </div>

      {/* Footer stats */}
      {scoredCount > 0 && (
        <div className="flex items-center justify-between px-1 pt-1 border-t border-white/[0.06]">
          <span className="text-[10px] font-mono text-white/25">
            Max: 120
          </span>
          <span className="text-[10px] font-mono text-white/25">
            Avg:{" "}
            {Math.round(
              sorted
                .filter((e) => e.status === "scored")
                .reduce((sum, e) => sum + (e.score ?? 0), 0) / scoredCount
            )}
          </span>
        </div>
      )}
    </div>
  );
}
