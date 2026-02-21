/**
 * AgentNode — Single agent status indicator (running/done/idle).
 * Used inside LayerDetail to show individual agent progress.
 *
 * See: docs/architecture/LLD_frontend.md § 5.3
 */

"use client";

import { motion } from "framer-motion";
import { Bot, CheckCircle2, Loader2, Circle } from "lucide-react";
import { type AgentState } from "@/hooks/useLayerStatus";
import { cn } from "@/lib/utils";

export function AgentNode({ agent }: { agent: AgentState }) {
  const isRunning = agent.status === "running";
  const isDone = agent.status === "done";

  return (
    <div className={cn(
      "group p-4 rounded-xl border flex items-center gap-4 transition-all duration-300",
      isRunning ? "bg-blue-500/10 border-blue-500/30 shadow-[0_0_15px_-5px_rgba(59,130,246,0.3)]" :
        isDone ? "bg-emerald-500/5 border-emerald-500/20" :
          "bg-white/[0.02] border-white/[0.05] hover:bg-white/[0.04]"
    )}>
      <div className="relative">
        <div className={cn(
          "w-10 h-10 rounded-xl flex items-center justify-center shadow-inner",
          isRunning ? "bg-blue-500/20 text-blue-400 ring-1 ring-blue-500/50" :
            isDone ? "bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/30" :
              "bg-white/5 text-white/20 ring-1 ring-white/10"
        )}>
          <Bot className="w-5 h-5" />
        </div>

        {/* Status Badge */}
        <div className="absolute -bottom-1 -right-1 bg-[#02040a] p-0.5 rounded-full ring-2 ring-[#02040a]">
          {isRunning ? (
            <Loader2 className="w-3.5 h-3.5 text-blue-400 animate-spin" />
          ) : isDone ? (
            <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
          ) : (
            <Circle className="w-3.5 h-3.5 text-white/20" />
          )}
        </div>
      </div>

      <div className="flex-1 min-w-0">
        <div className="flex items-center justify-between mb-0.5">
          <h4 className={cn(
            "text-sm font-semibold truncate",
            isRunning ? "text-blue-100" :
              isDone ? "text-emerald-100" :
                "text-white/60 group-hover:text-white/80"
          )}>
            {agent.name}
          </h4>
        </div>
        <p className="text-xs text-white/40 truncate font-mono">
          ID: {agent.id.slice(0, 8)}
        </p>
      </div>

      {isRunning && (
        <div className="w-1.5 h-1.5 rounded-full bg-blue-500 animate-pulse" />
      )}
    </div>
  );
}
