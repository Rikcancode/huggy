"""WebSocket manager for broadcasting list updates to connected clients."""
import asyncio
from fastapi import WebSocket


class ConnectionManager:
    def __init__(self):
        self.connections: set[WebSocket] = set()
        self._queue: asyncio.Queue[int | None] = asyncio.Queue()
        self._loop: asyncio.AbstractEventLoop | None = None

    def set_loop(self, loop: asyncio.AbstractEventLoop) -> None:
        self._loop = loop

    def notify_list_updated(self, list_id: int) -> None:
        """Call from sync code (e.g. after list mutation). Schedules broadcast."""
        if self._loop is None:
            return
        try:
            asyncio.run_coroutine_threadsafe(self._queue.put(list_id), self._loop)
        except Exception:
            pass

    async def connect(self, websocket: WebSocket) -> None:
        await websocket.accept()
        self.connections.add(websocket)

    def disconnect(self, websocket: WebSocket) -> None:
        self.connections.discard(websocket)

    async def broadcaster_task(self) -> None:
        """Run in lifespan: consume queue and broadcast to all connections."""
        while True:
            try:
                list_id = await asyncio.wait_for(self._queue.get(), timeout=30.0)
            except asyncio.TimeoutError:
                list_id = None
            if list_id is None:
                continue
            dead = []
            for ws in list(self.connections):
                try:
                    await ws.send_json({"type": "list_updated", "list_id": list_id})
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections.discard(ws)
