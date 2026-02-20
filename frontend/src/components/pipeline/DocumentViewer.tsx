/**
 * DocumentViewer — Renders a markdown document inline.
 * Used to view F1, F2, mx.md, and conversation logs.
 *
 * See: docs/architecture/LLD_frontend.md § 5.3
 */

"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { FileText, ChevronDown, Check } from "lucide-react";
import { type ArtifactState } from "@/hooks/useLayerStatus";
import { cn } from "@/lib/utils";

export function DocumentViewer({ document }: { document: ArtifactState }) {
  const [expanded, setExpanded] = useState(false);

  return (
    <motion.div
      layout
      className={cn(
        "rounded-xl border overflow-hidden transition-all duration-300",
        expanded ? "bg-white/[0.04] border-blue-500/30 shadow-lg ring-1 ring-blue-500/20" :
          "bg-white/[0.02] border-white/[0.05] hover:bg-white/[0.04] hover:border-white/10"
      )}
    >
      <div
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-4 p-4 cursor-pointer group"
      >
        <div className={cn(
          "w-10 h-10 rounded-lg flex items-center justify-center transition-colors",
          expanded ? "bg-blue-500/20 text-blue-400" : "bg-white/5 text-white/30 group-hover:bg-white/10"
        )}>
          <FileText className="w-5 h-5" />
        </div>

        <div className="flex-1 min-w-0">
          <h4 className="text-sm font-medium text-white/90 truncate group-hover:text-white">{document.title}</h4>
          <div className="flex items-center gap-2 mt-0.5">
            <span className="text-[10px] font-mono uppercase tracking-wider text-white/40 bg-white/5 px-1.5 py-0.5 rounded">
              {document.type}
            </span>
            <span className="text-[10px] text-emerald-500/80 flex items-center gap-1">
              <Check className="w-3 h-3" /> Generated
            </span>
          </div>
        </div>

        <motion.div
          animate={{ rotate: expanded ? 180 : 0 }}
          className={cn("transition-colors", expanded ? "text-blue-400" : "text-white/20")}
        >
          <ChevronDown className="w-5 h-5" />
        </motion.div>
      </div>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            className="border-t border-white/[0.05]"
          >
            <div className="p-6 bg-black/20">
              <pre className="text-xs md:text-sm text-white/70 font-mono whitespace-pre-wrap leading-relaxed max-h-[400px] overflow-y-auto custom-scrollbar pr-2">
                {document.content}
              </pre>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
