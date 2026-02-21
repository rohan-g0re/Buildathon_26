/**
 * LayerDetail — Zoomed-in view: agents + documents inside a layer.
 * Expands from LayerCard via shared layoutId transition.
 *
 * For Layer 3 (Sandbox), renders a real-time chat interface instead
 * of the standard agents + artifacts layout.
 *
 * See: docs/architecture/LLD_frontend.md § 5.3
 */

"use client";

import { useState, useCallback } from "react";
import { motion } from "framer-motion";
import { X, Cpu, FileText, MessageSquare } from "lucide-react";
import { type LayerState } from "@/hooks/useLayerStatus";
import { type SSEEvent } from "@/hooks/useSSE";
import { AgentNode } from "./AgentNode";
import { DocumentViewer } from "./DocumentViewer";
import { SandboxChatView } from "./SandboxChatView";
import { SandboxLeaderboard } from "./SandboxLeaderboard";
import { cn } from "@/lib/utils";

interface LayerDetailProps {
  layer: LayerState;
  onClose: () => void;
  events?: SSEEvent[];
}

export function LayerDetail({ layer, onClose, events }: LayerDetailProps) {
  const isSandbox = layer.id === "layer3";

  const [selectedMoveId, setSelectedMoveId] = useState<string | null>(null);

  const handleSelectMove = useCallback((moveId: string) => {
    setSelectedMoveId(moveId);
  }, []);

  return (
    <motion.div
      layoutId={`layer-${layer.id}`}
      className={cn(
        "fixed inset-4 md:inset-12 lg:inset-24 z-50 rounded-[40px] overflow-hidden",
        "bg-[#02040a] border border-white/10 shadow-2xl",
        "flex flex-col"
      )}
      transition={{ type: "spring", stiffness: 150, damping: 25 }}
    >
      {/* Modal Gradient Background */}
      <div className={cn(
        "absolute inset-0 pointer-events-none",
        isSandbox
          ? "bg-gradient-to-br from-purple-500/5 via-transparent to-red-500/5"
          : "bg-gradient-to-br from-blue-500/5 via-transparent to-purple-500/5"
      )} />

      {/* Header */}
      <div className="relative z-10 flex items-center justify-between p-8 border-b border-white/[0.08] backdrop-blur-xl bg-white/[0.02]">
        <div className="flex items-center gap-4">
          <div className={cn(
            "w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg",
            isSandbox
              ? "bg-gradient-to-br from-purple-500 to-pink-600 shadow-purple-500/20"
              : "bg-gradient-to-br from-blue-500 to-indigo-600 shadow-blue-500/20"
          )}>
            {isSandbox ? (
              <MessageSquare className="text-white w-6 h-6" />
            ) : (
              <Cpu className="text-white w-6 h-6" />
            )}
          </div>
          <div>
            <h2 className="text-3xl font-bold text-white tracking-tight">{layer.name}</h2>
            <p className="text-sm text-white/50">{layer.description}</p>
          </div>
        </div>
        <button
          onClick={onClose}
          className="w-10 h-10 rounded-full bg-white/5 hover:bg-white/10 flex items-center justify-center transition-colors text-white/60 hover:text-white"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Content */}
      <div className="relative z-10 flex-1 p-8 overflow-hidden">
        {isSandbox && events ? (
          /* Layer 3 — Leaderboard + Chat two-panel layout */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 h-full">
            <div className="lg:col-span-4 xl:col-span-3 h-full overflow-hidden border-r border-white/[0.06] pr-4">
              <SandboxLeaderboard
                events={events}
                selectedMoveId={selectedMoveId}
                onSelectMove={handleSelectMove}
              />
            </div>
            <div className="lg:col-span-8 xl:col-span-9 h-full overflow-hidden">
              <SandboxChatView
                events={events}
                selectedMoveId={selectedMoveId}
                onSelectMove={handleSelectMove}
              />
            </div>
          </div>
        ) : (
          /* Standard layout: agents + artifacts */
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 h-full overflow-y-auto custom-scrollbar">
            {/* Left Column: Agents */}
            <div className="lg:col-span-4 flex flex-col gap-6 border-r border-white/[0.05] pr-8">
              <div className="flex items-center justify-between mb-2">
                <h3 className="text-sm font-bold text-white/80 uppercase tracking-widest">Active Agents</h3>
                <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded-md font-mono">
                  {layer.agents.length}/{layer.agentCount}
                </span>
              </div>

              <div className="space-y-3">
                {layer.agents.map(agent => (
                  <AgentNode key={agent.id} agent={agent} />
                ))}
                {layer.agents.length === 0 && (
                  <div className="p-8 border border-dashed border-white/10 rounded-2xl text-center text-white/30 text-sm">
                    Waiting for agents to initialize...
                  </div>
                )}
              </div>
            </div>

            {/* Right Column: Artifacts */}
            <div className="lg:col-span-8 flex flex-col gap-6 pl-4">
              <div className="flex items-center gap-2 mb-2">
                <FileText className="w-4 h-4 text-white/40" />
                <h3 className="text-sm font-bold text-white/80 uppercase tracking-widest">System Output</h3>
              </div>

              <div className="grid grid-cols-1 gap-4">
                {layer.artifacts.map(artifact => (
                  <DocumentViewer key={artifact.id} document={artifact} />
                ))}
                {layer.artifacts.length === 0 && (
                  <div className="col-span-full h-48 border border-dashed border-white/10 rounded-2xl flex flex-col items-center justify-center gap-3 text-white/30">
                    <div className="w-12 h-12 rounded-full bg-white/[0.03] flex items-center justify-center">
                      <FileText className="w-5 h-5 opacity-50" />
                    </div>
                    <p className="text-sm">No analysis documents generated yet.</p>
                  </div>
                )}
              </div>
            </div>
          </div>
        )}
      </div>
    </motion.div>
  );
}
