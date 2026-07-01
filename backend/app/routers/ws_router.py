"""WebSocket router — real-time task status updates via Redis pub/sub."""
import asyncio
import json
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.core.logging import get_logger

router = APIRouter(tags=["WebSocket"])
logger = get_logger(__name__)


class ConnectionManager:
    """Manages active WebSocket connections per user."""

    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)
        logger.info("WS connected user_id=%s total=%s", user_id, len(self._connections.get(user_id, [])))

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        logger.info("WS disconnected user_id=%s", user_id)

    async def send_to_user(self, user_id: int, data: dict) -> None:
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                pass


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(ws: WebSocket, user_id: int):
    """
    WebSocket endpoint for real-time task execution updates.

    The client connects with their user_id.
    The server subscribes to Redis channel 'task_events' and forwards
    events that belong to this user.

    Connect from frontend:
        const ws = new WebSocket(`ws://localhost:8000/api/v1/ws/${userId}`);
    """
    await manager.connect(user_id, ws)
    try:
        from app.core.config import get_settings
        import redis.asyncio as aioredis

        settings = get_settings()
        r = aioredis.from_url(settings.REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe("task_events")

        async def listen():
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        data = json.loads(msg["data"])
                        # In production, filter by user_id by looking up task ownership.
                        # For the demo, broadcast to all connections.
                        await manager.send_to_user(user_id, data)
                    except Exception:
                        pass

        listen_task = asyncio.create_task(listen())

        # Keep connection alive, wait for client disconnect
        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "ping"}))
            except WebSocketDisconnect:
                break

        listen_task.cancel()
        await pubsub.unsubscribe("task_events")
        await r.aclose()

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(user_id, ws)
