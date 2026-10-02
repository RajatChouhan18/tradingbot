"""
txcore.stream
~~~~~~~~~~~~~
High-performance asynchronous Server-Sent Events (SSE) broadcaster and telemetry dispatcher.
Broadcasts real-time events (scan cycles, signals, ticks, logs, heartbeats) to connected frontend clients.
"""

import asyncio
import json
import logging
from typing import Set, Dict, Any, Optional
from datetime import datetime, timezone

logger = logging.getLogger(__name__)


class TelemetryBroadcaster:
    """
    Thread-safe SSE event broadcaster.
    Allows background threads (scanners, notifiers, schedulers) to push events
    to asyncio queues that stream directly to connected web clients.
    """

    def __init__(self):
        self._subscribers: Set[asyncio.Queue] = set()
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def set_event_loop(self, loop: asyncio.AbstractEventLoop):
        self._loop = loop

    def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        logger.debug(f"SSE client connected. Active subscribers: {len(self._subscribers)}")
        return queue

    def unsubscribe(self, queue: asyncio.Queue):
        self._subscribers.discard(queue)
        logger.debug(f"SSE client disconnected. Active subscribers: {len(self._subscribers)}")

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        """Asynchronously dispatches an event to all connected subscriber queues."""
        if not self._subscribers:
            return

        payload = f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
        dead_queues = []
        for q in list(self._subscribers):
            try:
                if q.full():
                    try:
                        q.get_nowait()
                    except asyncio.QueueEmpty:
                        pass
                q.put_nowait(payload)
            except Exception:
                dead_queues.append(q)

        for dq in dead_queues:
            self._subscribers.discard(dq)

    def broadcast_sync(self, event_type: str, data: Dict[str, Any]):
        """Thread-safe synchronous push from background worker threads into the event loop."""
        if not self._subscribers:
            return

        if self._loop and self._loop.is_running():
            try:
                self._loop.call_soon_threadsafe(
                    asyncio.create_task,
                    self.broadcast(event_type, data),
                )
            except Exception as e:
                logger.debug(f"Failed to schedule broadcast_sync: {e}")
        else:
            try:
                loop = asyncio.get_running_loop()
                if loop and loop.is_running():
                    loop.create_task(self.broadcast(event_type, data))
            except RuntimeError:
                pass


# Global singleton instance
telemetry_broadcaster = TelemetryBroadcaster()
