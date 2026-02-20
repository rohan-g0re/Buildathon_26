/**
 * usePipelineZoom — Zoom state management (which layer is zoomed).
 *
 * See: docs/architecture/LLD_frontend.md § 7
 */

import { useState, useCallback } from "react";

export function usePipelineZoom() {
  const [zoomedLayer, setZoomedLayer] = useState<string | null>(null);

  const zoomIn = useCallback((layerId: string) => {
    setZoomedLayer(layerId);
  }, []);

  const zoomOut = useCallback(() => {
    setZoomedLayer(null);
  }, []);

  return {
    zoomedLayer,
    setZoomedLayer,
    zoomIn,
    zoomOut,
    isZoomed: zoomedLayer !== null,
  };
}
