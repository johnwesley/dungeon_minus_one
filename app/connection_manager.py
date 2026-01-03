"""Connection manager for graceful shutdown and SSE connection tracking."""

import asyncio

from app.metrics import LLM_SESSION_ACTIVE


class ConnectionManager:
    """Manages active SSE connections for graceful shutdown."""

    def __init__(self):
        self.active_connections: set = set()
        self.shutdown_event = asyncio.Event()
        self._lock = asyncio.Lock()

    async def register(self, connection_id: str):
        async with self._lock:
            self.active_connections.add(connection_id)
            LLM_SESSION_ACTIVE.inc()

    async def unregister(self, connection_id: str):
        async with self._lock:
            self.active_connections.discard(connection_id)
            LLM_SESSION_ACTIVE.dec()

    def is_shutting_down(self) -> bool:
        return self.shutdown_event.is_set()

    async def wait_for_connections_to_drain(self, timeout: float = 30.0):
        """Wait for all active connections to complete, with timeout."""
        start_time = asyncio.get_event_loop().time()
        while self.active_connections:
            elapsed = asyncio.get_event_loop().time() - start_time
            if elapsed >= timeout:
                remaining = len(self.active_connections)
                print(f"Shutdown timeout: {remaining} connections still active, forcing close")
                break
            await asyncio.sleep(0.5)
        print("All connections drained or timeout reached")


# Singleton instance
connection_manager = ConnectionManager()
