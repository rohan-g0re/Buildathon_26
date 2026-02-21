/**
 * LayerCard — Individual layer card (status, progress ring).
 * Clickable to zoom in via layoutId shared element transition.
 *
 * See: docs/architecture/LLD_frontend.md § 5.2
 */

"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";
import { type LayerState } from "@/hooks/useLayerStatus";
import { CheckCircle2, RotateCw, AlertTriangle, PlayCircle } from "lucide-react";

interface LayerCardProps {
  layer: LayerState;
  onClick: () => void;
  index: number;
}

export function LayerCard({ layer, onClick, index }: LayerCardProps) {
  const isRunning = layer.status === "running";
  const isDone = layer.status === "done";
  const isError = layer.status === "error";

  return (
    <motion.div
      layoutId={`layer-${layer.id}`}
      onClick={onClick}
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: index * 0.1, duration: 0.5 }}
      className={cn(
        "relative w-[280px] h-[360px] rounded-[32px] cursor-pointer overflow-hidden border transition-all duration-300",
        // Glassmorphism base
        "bg-white/[0.03] backdrop-blur-md shadow-2xl",

        // Dynamic Border Colors based on state
        isRunning ? "border-blue-500/50 shadow-[0_0_40px_-10px_rgba(59,130,246,0.5)]" :
          isDone ? "border-emerald-500/30 shadow-[0_0_20px_-5px_rgba(16,185,129,0.3)]" :
            isError ? "border-red-500/50 shadow-[0_0_20px_-5px_rgba(239,68,68,0.3)]" :
              "border-white/[0.08] hover:border-white/[0.2] hover:bg-white/[0.06]"
      )}
      whileHover={{ y: -5, scale: 1.02 }}
    >
      {/* Background Gradient Glow */}
      <div className={cn(
        "absolute inset-0 bg-gradient-to-b from-transparent via-transparent to-black/80 pointer-events-none",
        isRunning && "opacity-80",
        !isRunning && "opacity-40"
      )} />

      {/* Top Glow Spot */}
      <div className={cn(
        "absolute -top-20 -right-20 w-40 h-40 rounded-full blur-[60px] pointer-events-none",
        isRunning ? "bg-blue-500/40" :
          isDone ? "bg-emerald-500/30" :
            "bg-white/[0.05]"
      )} />

      {/* Content Container */}
      <div className="relative h-full flex flex-col justify-between p-8">
        {/* Header */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-mono font-medium text-white/40 uppercase tracking-widest bg-white/[0.05] px-3 py-1 rounded-full">
              Layer {index}
            </span>
            <StatusIcon status={layer.status} />
          </div>

          <h3 className="text-2xl font-bold text-white tracking-tight leading-tight mb-2 break-words">
            {layer.name}
          </h3>
          <p className="text-sm text-white/50 leading-relaxed line-clamp-2">
            {layer.description}
          </p>
        </div>

        {/* Footer / Stats */}
        <div>
          {/* Progress Bar (if running) */}
          {isRunning && (
            <div className="mb-4">
              <div className="flex justify-between text-xs text-blue-200 mb-1.5 font-medium">
                <span>Processing...</span>
                <span>{Math.round(layer.progress)}%</span>
              </div>
              <div className="h-1.5 w-full bg-white/10 rounded-full overflow-hidden">
                <motion.div
                  className="h-full bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.8)]"
                  initial={{ width: 0 }}
                  animate={{ width: `${layer.progress}%` }}
                  transition={{ type: "spring", stiffness: 50 }}
                />
              </div>
            </div>
          )}

          <div className="flex items-center gap-3 pt-4 border-t border-white/[0.08]">
            <div className="flex -space-x-2">
              {/* Fake agent avatars */}
              {[...Array(Math.min(3, layer.agentCount))].map((_, i) => (
                <div key={i} className="w-8 h-8 rounded-full border-2 border-[#02040a] bg-white/10 flex items-center justify-center text-[10px] text-white/60">
                  A{i + 1}
                </div>
              ))}
              {layer.agentCount > 3 && (
                <div className="w-8 h-8 rounded-full border-2 border-[#02040a] bg-white/5 flex items-center justify-center text-[10px] text-white/40">
                  +{layer.agentCount - 3}
                </div>
              )}
            </div>
            <span className="text-xs text-white/40 font-medium ml-auto">
              {layer.agentCount} Agents
            </span>
          </div>
        </div>
      </div>
    </motion.div>
  );
}

function StatusIcon({ status }: { status: string }) {
  if (status === "running") {
    return (
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ duration: 2, repeat: Infinity, ease: "linear" }}
      >
        <RotateCw className="w-5 h-5 text-blue-400" />
      </motion.div>
    )
  }
  if (status === "done") {
    return <CheckCircle2 className="w-5 h-5 text-emerald-400" />
  }
  if (status === "error") {
    return <AlertTriangle className="w-5 h-5 text-red-400" />
  }
  return (
    <motion.div
      animate={{ rotate: 360 }}
      transition={{ duration: 4, repeat: Infinity, ease: "linear" }}
    >
      <RotateCw className="w-5 h-5 text-white/20" />
    </motion.div>
  )
}
