/**
 * useSSE — SSE connection hook (connect, parse events, reconnect).
 *
 * See: docs/architecture/LLD_frontend.md § 6
 */

import { useEffect, useState } from "react";

export interface SSEEvent {
  event: string;
  [key: string]: any;
}

export function useSSE(analysisId: string) {
  const [events, setEvents] = useState<SSEEvent[]>([]);
  const [status, setStatus] = useState<
    "connecting" | "connected" | "done" | "error"
  >("connecting");

  useEffect(() => {
    // Connect directly to the backend, bypassing Next.js rewrite proxy.
    // The proxy has a ~30s timeout that kills long-lived SSE streams.
    const backendUrl =
      process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:8000";
    const source = new EventSource(
      `${backendUrl}/api/stream/${analysisId}`
    );

    source.onopen = () => setStatus("connected");

    source.onmessage = (e) => {
      const event: SSEEvent = JSON.parse(e.data);
      setEvents((prev) => [...prev, event]);

      if (event.event === "pipeline_complete") {
        setStatus("done");
        source.close();
      }
      if (event.event === "pipeline_error") {
        setStatus("error");
        source.close();
      }
    };

    source.onerror = () => {
      // EventSource fires onerror on temporary disconnects and will
      // auto-reconnect. Only treat it as fatal if the browser gave up.
      if (source.readyState === EventSource.CLOSED) {
        setStatus("error");
      }
    };

    return () => source.close();
  }, [analysisId]);

  return { events, status };
}
