from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
import logging
import time
from typing import Any, Dict, Optional
from typing import Dict, Optional
from uuid import uuid4

from fastapi import WebSocket

logger = logging.getLogger(__name__)


@dataclass
class _Connection:
    websocket: WebSocket
    queue: asyncio.Queue
    created_at: float = field(default_factory=time.time)
    last_pong: float = field(default_factory=time.time)
    heartbeat_task: Optional[asyncio.Task] = None
    sender_task: Optional[asyncio.Task] = None
    dropped_messages: int = 0


class WebSocketBroker:
    """Enhanced broker with heartbeat, reconnect metadata, and backpressure control."""

    def __init__(self, channel_name: str = "", queue_size: int = 64) -> None:
        self.channel_name = channel_name
        self.queue_size = queue_size
        self._connections_by_id: Dict[str, _Connection] = {}
        self._index_by_ws: Dict[WebSocket, str] = {}
        self._lock = asyncio.Lock()
        self.ping_interval = 30  # seconds
        self.pong_timeout = 10  # seconds

    async def register_connection(self, websocket: WebSocket) -> str:
        # TIDAK panggil websocket.accept() lagi, karena sudah di-accept di handler
        connection_id = str(uuid4())
        logger.info(f"[{self.channel_name}] New connection request. Assigned ID: {connection_id}")
        queue: asyncio.Queue = asyncio.Queue(maxsize=self.queue_size)
        conn = _Connection(websocket=websocket, queue=queue)
        async with self._lock:
            self._connections_by_id[connection_id] = conn
            self._index_by_ws[websocket] = connection_id

        conn.sender_task = asyncio.create_task(self._sender_loop(connection_id))
        conn.heartbeat_task = asyncio.create_task(self._heartbeat_loop(connection_id))
        
        await asyncio.sleep(0)  # Keep this untuk task scheduling
        
        logger.info("[%s] connection %s opened successfully", self.channel_name, connection_id)
        return connection_id

    def disconnect(self, identifier) -> None:
        if isinstance(identifier, WebSocket):
            connection_id = self._index_by_ws.pop(identifier, None)
        else:
            connection_id = identifier

        if connection_id is None:
            logger.warning(f"[{self.channel_name}] Attempted to disconnect unknown identifier: {identifier}")
            return

        conn = self._connections_by_id.pop(connection_id, None)
        if not conn:
            return

        self._index_by_ws.pop(conn.websocket, None)

        if conn.heartbeat_task:
            conn.heartbeat_task.cancel()
        if conn.sender_task:
            conn.sender_task.cancel()

        try:
            conn.queue.put_nowait(None)
        except asyncio.QueueFull:
            pass

        asyncio.create_task(self._safe_close(conn.websocket))
        logger.info("[%s] connection %s closed", self.channel_name, connection_id)

    async def _safe_close(self, websocket: WebSocket) -> None:
        try:
            await websocket.close(code=1000)
        except Exception:
            pass

    async def _sender_loop(self, connection_id: str) -> None:
        while True:
            async with self._lock:
                conn = self._connections_by_id.get(connection_id)
            if not conn:
                break
            try:
                message = await conn.queue.get()
            except asyncio.CancelledError:
                break
            if message is None:
                break
            try:
                if conn.dropped_messages:
                    status_message = {
                        "type": "status",
                        "channel": self.channel_name,
                        "status": "backpressure_drop",
                        "dropped": conn.dropped_messages,
                    }
                    await conn.websocket.send_json(status_message)
                    conn.dropped_messages = 0
                await conn.websocket.send_json(message)
            except Exception:
                break
        self.disconnect(connection_id)

    async def _heartbeat_loop(self, connection_id: str) -> None:
        while True:
            await asyncio.sleep(self.ping_interval)
            async with self._lock:
                conn = self._connections_by_id.get(connection_id)
            if not conn:
                break
            now = time.time()
            if now - conn.last_pong > self.ping_interval + self.pong_timeout:
                logger.warning(
                    "[%s] heartbeat timeout for %s", self.channel_name, connection_id
                )
                break
            try:
                await conn.websocket.send_json(
                    {
                        "type": "heartbeat",
                        "channel": self.channel_name,
                        "timestamp": time.time(),
                    }
                )
            except Exception:
                break
        self.disconnect(connection_id)

    def handle_pong(self, websocket: WebSocket) -> None:
        connection_id = self._index_by_ws.get(websocket)
        if connection_id is None:
            return
        conn = self._connections_by_id.get(connection_id)
        if conn:
            conn.last_pong = time.time()

    async def broadcast(self, message: Dict[str, Any]) -> None:
        async with self._lock:
            snapshot = list(self._connections_by_id.items())
        for connection_id, conn in snapshot:
            self._enqueue_message(conn, message)

    def _enqueue_message(self, conn: _Connection, message: Dict[str, Any]) -> None:
        if conn.queue.full():
            try:
                conn.queue.get_nowait()
            except asyncio.QueueEmpty:
                pass
            conn.dropped_messages += 1
        try:
            conn.queue.put_nowait(message)
        except asyncio.QueueFull:
            conn.dropped_messages += 1

    async def close(self) -> None:
        async with self._lock:
            identifiers = list(self._connections_by_id.keys())
        for conn_id in identifiers:
            self.disconnect(conn_id)
        await asyncio.sleep(0)


# Instantiate brokers for each channel
_gaze_broker = WebSocketBroker("gaze")
_pose_broker = WebSocketBroker("pose")
_stress_broker = WebSocketBroker("stress")

gaze_broker = _gaze_broker
pose_broker = _pose_broker
stress_broker = _stress_broker

__all__ = ["gaze_broker", "pose_broker", "stress_broker", "WebSocketBroker"]
