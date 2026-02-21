/**
 * useLayerStatus — Derives layer states from real SSE events.
 *
 * Maps backend events (layer_start, layer_complete, agent_complete)
 * to UI layer state for the pipeline visualization.
 *
 * See: docs/architecture/LLD_frontend.md § 8
 */

import { useMemo } from "react";
import { type SSEEvent } from "./useSSE";

export interface AgentState {
  id: string;
  name: string;
  status: "idle" | "running" | "done" | "error";
}

export interface ArtifactState {
  id: string;
  title: string;
  type: string;
  content: string;
}

export interface LayerState {
  id: string;
  name: string;
  description: string;
  status: "idle" | "running" | "done" | "error";
  progress: number;
  agentCount: number;
  agents: AgentState[];
  artifacts: ArtifactState[];
}

const INITIAL_LAYERS: LayerState[] = [
  {
    id: "layer0",
    name: "Data Gathering",
    description: "Synthesizing financial & news data",
    status: "idle",
    progress: 0,
    agentCount: 2,
    agents: [],
    artifacts: [],
  },
  {
    id: "layer1",
    name: "Inference",
    description: "Deriving insights from raw data",
    status: "idle",
    progress: 0,
    agentCount: 2,
    agents: [],
    artifacts: [],
  },
  {
    id: "layer2",
    name: "Analysis",
    description: "Generating strategic moves",
    status: "idle",
    progress: 0,
    agentCount: 5,
    agents: [],
    artifacts: [],
  },
  {
    id: "layer3",
    name: "Sandbox",
    description: "Negotiation & scoring of strategic moves",
    status: "idle",
    progress: 0,
    agentCount: 3,
    agents: [],
    artifacts: [],
  },
];

/**
 * Maps a backend layer number (0, 1, 2, 3) to the frontend layer id.
 */
function layerIdFromNumber(layer: number): string {
  return `layer${layer}`;
}

export function useLayerStatus(events: SSEEvent[]): LayerState[] {
  return useMemo(() => {
    // Deep-copy initial state to avoid mutation across renders
    const layers: LayerState[] = JSON.parse(JSON.stringify(INITIAL_LAYERS));

    for (const event of events) {
      const layerId = event.layer !== undefined ? layerIdFromNumber(event.layer) : null;
      const layer = layerId ? layers.find((l) => l.id === layerId) : null;

      switch (event.event) {
        case "layer_start": {
          if (layer) {
            layer.status = "running";
            layer.progress = 0;
          }
          break;
        }

        case "layer_complete": {
          if (layer) {
            layer.status = "done";
            layer.progress = 100;
          }
          break;
        }

        case "agent_complete": {
          if (layer) {
            // Add agent to the completed list (avoid duplicates)
            const agentId = event.agent_id || "unknown";
            if (!layer.agents.find((a) => a.id === agentId)) {
              layer.agents.push({
                id: agentId,
                name: event.persona || event.agent_id || "Agent",
                status: "done",
              });
            }
            // Update progress based on how many agents are done
            if (layer.agentCount > 0) {
              layer.progress = Math.min(
                100,
                Math.round(
                  (layer.agents.filter((a) => a.status === "done").length /
                    layer.agentCount) *
                    100
                )
              );
            }
          }
          break;
        }

        case "sandbox_move_start": {
          const startLayer = layers.find((l) => l.id === "layer3");
          if (startLayer) {
            startLayer.status = "running";
            startLayer.progress = Math.min(95, startLayer.progress + 1);
          }
          break;
        }

        case "sandbox_round": {
          // A negotiation round completed for a move — update layer3 progress
          const sandboxLayer = layers.find((l) => l.id === "layer3");
          if (sandboxLayer) {
            sandboxLayer.status = "running";
            // Increment progress slightly with each round event
            sandboxLayer.progress = Math.min(
              95,
              sandboxLayer.progress + 2
            );
          }
          break;
        }

        case "sandbox_scored": {
          // A move has been fully scored — track it as an agent completion on layer3
          const scoredLayer = layers.find((l) => l.id === "layer3");
          if (scoredLayer) {
            scoredLayer.status = "running";
            const moveId = event.move || "unknown";
            if (!scoredLayer.agents.find((a) => a.id === moveId)) {
              scoredLayer.agents.push({
                id: moveId,
                name: `${moveId} (Score: ${event.score ?? "?"}/120)`,
                status: "done",
              });
            }
          }
          break;
        }

        case "sandbox_skipped": {
          // A move was skipped — track it on layer3
          const skippedLayer = layers.find((l) => l.id === "layer3");
          if (skippedLayer) {
            skippedLayer.status = "running";
            const moveId = event.move || "unknown";
            if (!skippedLayer.agents.find((a) => a.id === moveId)) {
              skippedLayer.agents.push({
                id: moveId,
                name: `${moveId} (Skipped)`,
                status: "done",
              });
            }
          }
          break;
        }

        case "pipeline_complete": {
          // Mark all layers as done (in case any were missed)
          for (const l of layers) {
            if (l.status === "running") {
              l.status = "done";
              l.progress = 100;
            }
          }
          break;
        }

        case "pipeline_error": {
          // Mark current running layer as error
          for (const l of layers) {
            if (l.status === "running") {
              l.status = "error";
            }
          }
          break;
        }
      }
    }

    return layers;
  }, [events]);
}
