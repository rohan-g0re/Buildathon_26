/**
 * SandboxChatView — Real-time chat interface for Layer 3 (Sandbox).
 *
 * Displays a single shared conversation: Critic vs Decision Makers.
 * Critic messages appear on the left, DM messages on the right.
 * All 3 DMs respond in parallel each round (boardroom model).
 * Auto-scrolls as new messages arrive via SSE.
 */

"use client";

import { useMemo, useRef, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { MessageSquare, Bot, Shield } from "lucide-react";
import { type SSEEvent } from "@/hooks/useSSE";
import { cn } from "@/lib/utils";
import { MarkdownRenderer } from "@/components/ui/MarkdownRenderer";

interface ChatMessage {
  role: string;   // "critic" | "D1" | "D2" | "D3"
  content: string;
  round: number;
}

const DM_COLORS: Record<string, { bg: string; border: string; text: string; badge: string }> = {
  D1: { bg: "bg-purple-500/10", border: "border-purple-500/20", text: "text-purple-100/80", badge: "text-purple-400/70" },
  D2: { bg: "bg-blue-500/10", border: "border-blue-500/20", text: "text-blue-100/80", badge: "text-blue-400/70" },
  D3: { bg: "bg-emerald-500/10", border: "border-emerald-500/20", text: "text-emerald-100/80", badge: "text-emerald-400/70" },
};
const DM_ICON_COLORS: Record<string, { bg: string; ring: string; icon: string }> = {
  D1: { bg: "bg-purple-500/15", ring: "ring-purple-500/30", icon: "text-purple-400" },
  D2: { bg: "bg-blue-500/15", ring: "ring-blue-500/30", icon: "text-blue-400" },
  D3: { bg: "bg-emerald-500/15", ring: "ring-emerald-500/30", icon: "text-emerald-400" },
};
const DM_NAMES: Record<string, string> = {
  D1: "Growth Strategist",
  D2: "Operational Pragmatist",
  D3: "Stakeholder Advocate",
};

interface SandboxChatViewProps {
  events: SSEEvent[];
  selectedMoveId?: string | null;
  onSelectMove?: (moveId: string) => void;
}

export function SandboxChatView({ events, selectedMoveId, onSelectMove }: SandboxChatViewProps) {
  const scrollRef = useRef<HTMLDivElement>(null);
  const hasExternalControl = selectedMoveId !== undefined && onSelectMove !== undefined;

  // Current move (last one with sandbox_round events)
  const currentMove = useMemo(() => {
    for (let i = events.length - 1; i >= 0; i--) {
      if (events[i].event === "sandbox_round" && events[i].move) {
        return events[i].move as string;
      }
    }
    return null;
  }, [events]);

  const [internalSelected, setInternalSelected] = useState<string | null>(null);
  const [userPickedMove, setUserPickedMove] = useState(false);

  // Auto-follow latest move when no user/external selection
  useEffect(() => {
    if (hasExternalControl) {
      if (!selectedMoveId && currentMove) {
        onSelectMove(currentMove);
      }
    } else if (!userPickedMove && currentMove) {
      setInternalSelected(currentMove);
    }
  }, [currentMove, userPickedMove, hasExternalControl, selectedMoveId, onSelectMove]);

  const activeMove = hasExternalControl
    ? (selectedMoveId || currentMove)
    : (internalSelected || currentMove);

  const handlePickMove = (moveId: string) => {
    if (hasExternalControl) {
      onSelectMove(moveId);
    } else {
      setInternalSelected(moveId);
      setUserPickedMove(true);
    }
  };

  // Derive move IDs from events
  const moveIds = useMemo(() => {
    const ids = new Set<string>();
    for (const event of events) {
      if (event.event === "sandbox_round" && event.move) {
        ids.add(event.move as string);
      }
    }
    return Array.from(ids);
  }, [events]);

  // Filter messages for the active move
  const filteredMessages = useMemo(() => {
    const msgs: ChatMessage[] = [];
    for (const event of events) {
      if (event.event === "sandbox_round" && event.messages) {
        const eventMove = event.move as string;
        if (activeMove && eventMove !== activeMove) continue;
        for (const msg of event.messages as ChatMessage[]) {
          msgs.push(msg);
        }
      }
    }
    return msgs;
  }, [events, activeMove]);

  // Count scored moves
  const scoredMoves = useMemo(() => {
    const scored: Record<string, number> = {};
    for (const event of events) {
      if (event.event === "sandbox_scored") {
        scored[event.move as string] = event.score as number;
      }
    }
    return scored;
  }, [events]);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [filteredMessages.length]);

  // Current round from filtered messages
  const currentRound = filteredMessages.length > 0
    ? filteredMessages[filteredMessages.length - 1].round
    : 0;

  return (
    <div className="flex flex-col h-full gap-4">
      {/* Move selector (if multiple moves and no external leaderboard) */}
      {!hasExternalControl && moveIds.length > 0 && (
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-xs font-mono text-white/40 uppercase tracking-wider mr-1">
            Move:
          </span>
          {moveIds.map((mid) => {
            const isActive = activeMove === mid;
            const score = scoredMoves[mid];
            return (
              <button
                key={mid}
                onClick={() => handlePickMove(mid)}
                className={cn(
                  "px-3 py-1 rounded-lg text-xs font-mono transition-all duration-200",
                  isActive
                    ? "bg-purple-500/20 text-purple-300 border border-purple-500/40"
                    : "bg-white/5 text-white/40 border border-white/[0.08] hover:bg-white/10 hover:text-white/60"
                )}
              >
                {mid}
                {score !== undefined && (
                  <span className="ml-1.5 text-emerald-400">{score}/120</span>
                )}
              </button>
            );
          })}
        </div>
      )}

      {/* Round indicator */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <MessageSquare className="w-3.5 h-3.5 text-white/30" />
          <span className="text-xs text-white/40 font-mono">
            {filteredMessages.length > 0
              ? `Round ${currentRound} — ${filteredMessages.length} messages`
              : "Waiting for negotiation to start..."}
          </span>
        </div>
        {activeMove && scoredMoves[activeMove] !== undefined && (
          <span className="text-xs font-mono text-emerald-400 bg-emerald-500/10 px-2 py-0.5 rounded-md">
            Final: {scoredMoves[activeMove]}/120
          </span>
        )}
      </div>

      {/* Chat messages */}
      <div
        ref={scrollRef}
        className="flex-1 overflow-y-auto custom-scrollbar space-y-3 pr-1 min-h-0"
      >
        {filteredMessages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-white/20">
            <div className="w-14 h-14 rounded-full bg-white/[0.03] flex items-center justify-center">
              <MessageSquare className="w-6 h-6 opacity-50" />
            </div>
            <p className="text-sm">Negotiation messages will appear here in real-time.</p>
          </div>
        ) : (
          <AnimatePresence initial={false}>
            {filteredMessages.map((msg, idx) => {
              const isCritic = msg.role === "critic";
              const roundChanged = idx === 0 || filteredMessages[idx - 1].round !== msg.round;

              // DM styling
              const dmColor = !isCritic ? (DM_COLORS[msg.role] || DM_COLORS.D1) : null;
              const dmIcon = !isCritic ? (DM_ICON_COLORS[msg.role] || DM_ICON_COLORS.D1) : null;
              const dmName = !isCritic ? (DM_NAMES[msg.role] || msg.role) : null;

              return (
                <div key={`${msg.round}-${msg.role}-${idx}`}>
                  {/* Round divider */}
                  {roundChanged && (
                    <div className="flex items-center gap-3 my-4">
                      <div className="flex-1 h-px bg-white/[0.06]" />
                      <span className="text-[10px] font-mono text-white/25 uppercase tracking-widest">
                        Round {msg.round}
                      </span>
                      <div className="flex-1 h-px bg-white/[0.06]" />
                    </div>
                  )}

                  <motion.div
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.25 }}
                    className={cn(
                      "flex gap-3",
                      isCritic ? "justify-start" : "justify-end"
                    )}
                  >
                    {/* Critic avatar (left) */}
                    {isCritic && (
                      <div className="flex-shrink-0 mt-1">
                        <div className="w-8 h-8 rounded-lg bg-red-500/15 flex items-center justify-center ring-1 ring-red-500/30">
                          <Shield className="w-4 h-4 text-red-400" />
                        </div>
                      </div>
                    )}

                    {/* Message bubble */}
                    <div
                      className={cn(
                        "max-w-[75%] rounded-2xl px-4 py-3 text-sm leading-relaxed",
                        isCritic
                          ? "bg-white/[0.04] border border-white/[0.08] text-white/70 rounded-tl-md"
                          : `${dmColor!.bg} ${dmColor!.border} border ${dmColor!.text} rounded-tr-md`
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1.5">
                        <span className={cn(
                          "text-[10px] font-bold uppercase tracking-wider",
                          isCritic ? "text-red-400/70" : dmColor!.badge
                        )}>
                          {isCritic ? "Critic" : `${msg.role} — ${dmName}`}
                        </span>
                      </div>
                      <MarkdownRenderer content={msg.content} compact />
                    </div>

                    {/* DM avatar (right) */}
                    {!isCritic && (
                      <div className="flex-shrink-0 mt-1">
                        <div className={cn(
                          "w-8 h-8 rounded-lg flex items-center justify-center ring-1",
                          dmIcon!.bg, dmIcon!.ring
                        )}>
                          <Bot className={cn("w-4 h-4", dmIcon!.icon)} />
                        </div>
                      </div>
                    )}
                  </motion.div>
                </div>
              );
            })}
          </AnimatePresence>
        )}
      </div>
    </div>
  );
}
