"""WebSocket router — real-time task status updates via Redis pub/sub."""
import asyncio
import json

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.core.logging import get_logger

router = APIRouter(tags=["WebSocket"])
logger = get_logger(__name__)


class ConnectionManager:
    def __init__(self) -> None:
        self._connections: dict[int, list[WebSocket]] = {}

    async def connect(self, user_id: int, ws: WebSocket) -> None:
        await ws.accept()
        self._connections.setdefault(user_id, []).append(ws)

    def disconnect(self, user_id: int, ws: WebSocket) -> None:
        conns = self._connections.get(user_id, [])
        if ws in conns:
            conns.remove(ws)
        if not conns:
            self._connections.pop(user_id, None)

    async def send_to_user(self, user_id: int, data: dict) -> None:
        for ws in list(self._connections.get(user_id, [])):
            try:
                await ws.send_text(json.dumps(data))
            except Exception:
                self.disconnect(user_id, ws)


manager = ConnectionManager()


@router.websocket("/ws/{user_id}")
async def websocket_endpoint(ws: WebSocket, user_id: int):
    await manager.connect(user_id, ws)
    channel = f"task_events:{user_id}"
    listen_task = None
    r = pubsub = None

    try:
        from app.core.config import get_settings
        import redis.asyncio as aioredis

        r = aioredis.from_url(get_settings().REDIS_URL, decode_responses=True)
        pubsub = r.pubsub()
        await pubsub.subscribe(channel)

        async def listen():
            async for msg in pubsub.listen():
                if msg["type"] == "message":
                    try:
                        await manager.send_to_user(user_id, json.loads(msg["data"]))
                    except Exception:
                        pass

        listen_task = asyncio.create_task(listen())

        while True:
            try:
                await asyncio.wait_for(ws.receive_text(), timeout=30)
            except asyncio.TimeoutError:
                await ws.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        pass
    finally:
        if listen_task:
            listen_task.cancel()
        if pubsub:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass
        if r:
            await r.aclose()
        manager.disconnect(user_id, ws)