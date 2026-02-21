"use client";

import { motion } from "framer-motion";
import { Crown } from "lucide-react";
import { type MoveResult } from "@/lib/types";
import { MoveCard } from "./MoveCard";

interface RecommendedMovesProps {
  moves: MoveResult[];
}

export function RecommendedMoves({ moves }: RecommendedMovesProps) {
  if (moves.length === 0) return null;

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2.5">
        <div className="w-8 h-8 rounded-lg bg-amber-500/15 flex items-center justify-center">
          <Crown className="w-4 h-4 text-amber-400" />
        </div>
        <div>
          <h2 className="text-base font-bold text-white/90">Recommended Moves</h2>
          <p className="text-[11px] text-white/35">Top 3 highest-scored strategic moves</p>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {moves.map((move, i) => (
          <motion.div
            key={move.move_id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: i * 0.1, duration: 0.4 }}
          >
            <MoveCard move={move} rank={i + 1} highlighted />
          </motion.div>
        ))}
      </div>
    </div>
  );
}
