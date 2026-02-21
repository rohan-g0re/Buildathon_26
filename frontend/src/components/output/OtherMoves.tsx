"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { ChevronDown, List } from "lucide-react";
import { type MoveResult } from "@/lib/types";
import { MoveCard } from "./MoveCard";

interface OtherMovesProps {
  moves: MoveResult[];
  startRank: number;
}

export function OtherMoves({ moves, startRank }: OtherMovesProps) {
  const [expanded, setExpanded] = useState(false);

  if (moves.length === 0) return null;

  return (
    <div className="space-y-3">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-2.5 group w-full"
      >
        <div className="w-8 h-8 rounded-lg bg-white/5 flex items-center justify-center group-hover:bg-white/10 transition-colors">
          <List className="w-4 h-4 text-white/30" />
        </div>
        <div className="flex-1 text-left">
          <h2 className="text-sm font-semibold text-white/50 group-hover:text-white/70 transition-colors">
            Other Moves ({moves.length})
          </h2>
          <p className="text-[10px] text-white/25">Remaining scored moves</p>
        </div>
        <motion.div
          animate={{ rotate: expanded ? 180 : 0 }}
          className="text-white/20 group-hover:text-white/40 transition-colors"
        >
          <ChevronDown className="w-4 h-4" />
        </motion.div>
      </button>

      <AnimatePresence>
        {expanded && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: "auto", opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.3 }}
            className="space-y-3 overflow-hidden"
          >
            {moves.map((move, i) => (
              <motion.div
                key={move.move_id}
                initial={{ opacity: 0, x: -10 }}
                animate={{ opacity: 1, x: 0 }}
                transition={{ delay: i * 0.05 }}
              >
                <MoveCard move={move} rank={startRank + i} highlighted={false} />
              </motion.div>
            ))}
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
