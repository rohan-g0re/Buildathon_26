"""
SSE stream manager — event queue and broadcast.

See: docs/architecture/LLD_pipeline.md § 6
"""

import asyncio
import json
import logging
from typing import AsyncGenerator

log = logging.getLogger("sse")


class SSEManager:
    """
    Manages Server-Sent Event streams for multiple concurrent analyses.
    Each analysis_id has its own list of subscriber queues.
    Events published before any subscriber connects are buffered and
    replayed when the first subscriber connects.
    """

    def __init__(self):
        self._queues: dict[str, list[asyncio.Queue]] = {}
        self._buffers: dict[str, list[str]] = {}

    async def publish(self, analysis_id: str, event: dict):
        """Publishes an event to all subscribers of an analysis."""
        data = json.dumps(event)
        short_id = analysis_id[:8]

        if analysis_id not in self._queues or not self._queues[analysis_id]:
            # No subscribers yet — buffer the event
            self._buffers.setdefault(analysis_id, []).append(data)
            log.info("[%s] BUFFERED (no subscribers): %s", short_id, event.get("event", "?"))
            return

        for queue in self._queues[analysis_id]:
            await queue.put(data)

    async def subscribe(self, analysis_id: str) -> AsyncGenerator[str, None]:
        """Returns an async generator that yields SSE-formatted events."""
        queue: asyncio.Queue = asyncio.Queue()
        short_id = analysis_id[:8]

        if analysis_id not in self._queues:
            self._queues[analysis_id] = []
        self._queues[analysis_id].append(queue)

        subscriber_count = len(self._queues[analysis_id])
        log.info("[%s] Subscriber connected (total: %d)", short_id, subscriber_count)

        # Replay buffered events
        buffered = self._buffers.pop(analysis_id, [])
        if buffered:
            log.info("[%s] Replaying %d buffered events", short_id, len(buffered))
            for data in buffered:
                await queue.put(data)

        try:
            while True:
                data = await queue.get()
                yield f"data: {data}\n\n"

                # Check for terminal events
                parsed = json.loads(data)
                if parsed.get("event") in ("pipeline_complete", "pipeline_error"):
                    break
        finally:
            if analysis_id in self._queues:
                self._queues[analysis_id].remove(queue)
                if not self._queues[analysis_id]:
                    del self._queues[analysis_id]
            log.info("[%s] Subscriber disconnected", short_id)
