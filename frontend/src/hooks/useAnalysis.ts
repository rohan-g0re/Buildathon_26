/**
 * useAnalysis — re-exports layer status hook.
 *
 * The real implementation lives in useLayerStatus.ts.
 * This file exists for backward compatibility with any imports from useAnalysis.
 *
 * See: docs/architecture/LLD_frontend.md § 8
 */

export { useLayerStatus } from "./useLayerStatus";
export type { LayerState, AgentState, ArtifactState } from "./useLayerStatus";
