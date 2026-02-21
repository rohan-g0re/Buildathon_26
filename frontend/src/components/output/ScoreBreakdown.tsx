"use client";

import {
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  Radar,
  ResponsiveContainer,
  Tooltip,
} from "recharts";
import { type ScoreBreakdown as ScoreBreakdownType } from "@/lib/types";

const METRICS = [
  { key: "impact", label: "Impact" },
  { key: "feasibility", label: "Feasibility" },
  { key: "risk_adjusted_return", label: "Risk-Adj Return" },
  { key: "strategic_alignment", label: "Strat Alignment" },
] as const;

const DM_CONFIG: Record<string, { color: string; label: string }> = {
  D1: { color: "#a855f7", label: "D1 Growth" },
  D2: { color: "#3b82f6", label: "D2 Ops" },
  D3: { color: "#10b981", label: "D3 Value" },
};

interface ScoreBreakdownProps {
  scoresByAgent: Record<string, ScoreBreakdownType>;
}

export function ScoreBreakdown({ scoresByAgent }: ScoreBreakdownProps) {
  const agentIds = Object.keys(scoresByAgent).filter((k) => DM_CONFIG[k]);

  if (agentIds.length === 0) return null;

  const data = METRICS.map(({ key, label }) => {
    const point: Record<string, string | number> = { metric: label };
    for (const agentId of agentIds) {
      const scores = scoresByAgent[agentId];
      point[agentId] = scores?.[key as keyof ScoreBreakdownType] ?? 0;
    }
    return point;
  });

  return (
    <div className="w-full h-[200px]">
      <ResponsiveContainer width="100%" height="100%">
        <RadarChart data={data} cx="50%" cy="50%" outerRadius="70%">
          <PolarGrid
            stroke="rgba(255,255,255,0.06)"
            strokeDasharray="3 3"
          />
          <PolarAngleAxis
            dataKey="metric"
            tick={{ fill: "rgba(255,255,255,0.4)", fontSize: 10 }}
          />
          <Tooltip
            contentStyle={{
              backgroundColor: "rgba(2,4,10,0.95)",
              border: "1px solid rgba(255,255,255,0.1)",
              borderRadius: "8px",
              fontSize: "12px",
              color: "rgba(255,255,255,0.7)",
            }}
          />
          {agentIds.map((agentId) => (
            <Radar
              key={agentId}
              name={DM_CONFIG[agentId]?.label ?? agentId}
              dataKey={agentId}
              stroke={DM_CONFIG[agentId]?.color ?? "#888"}
              fill={DM_CONFIG[agentId]?.color ?? "#888"}
              fillOpacity={0.15}
              strokeWidth={1.5}
              domain={[0, 10]}
            />
          ))}
        </RadarChart>
      </ResponsiveContainer>
      <div className="flex items-center justify-center gap-4 -mt-2">
        {agentIds.map((agentId) => (
          <div key={agentId} className="flex items-center gap-1.5">
            <div
              className="w-2 h-2 rounded-full"
              style={{ backgroundColor: DM_CONFIG[agentId]?.color }}
            />
            <span className="text-[10px] text-white/40">
              {DM_CONFIG[agentId]?.label ?? agentId}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
}
