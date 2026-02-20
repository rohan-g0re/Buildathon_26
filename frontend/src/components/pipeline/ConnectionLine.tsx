/**
 * ConnectionLine — Animated connection line between layer cards.
 * Glows cyan when data is flowing (layer is active).
 *
 * See: docs/architecture/LLD_frontend.md § 5.1
 */

"use client";

import { motion } from "framer-motion";
import { cn } from "@/lib/utils";

export function ConnectionLine({ active = false }: { active?: boolean }) {
  return (
    <div className="relative w-16 flex items-center justify-center">
      {/* Base line */}
      <div className="absolute h-[2px] w-full bg-white/[0.05] rounded-full" />

      {/* Active pulse */}
      {active && (
        <motion.div
          className="absolute h-[2px] w-full bg-gradient-to-r from-transparent via-blue-500 to-transparent shadow-[0_0_10px_rgba(59,130,246,0.8)]"
          initial={{ opacity: 0, x: "-100%" }}
          animate={{ opacity: [0, 1, 0], x: "100%" }}
          transition={{ duration: 1.5, repeat: Infinity, ease: "linear" }}
        />
      )}

      {/* Connection dot */}
      <div className={cn(
        "h-2 w-2 rounded-full relative z-10 transition-colors duration-500",
        active ? "bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,1)]" : "bg-white/10"
      )} />
    </div>
  );
}
