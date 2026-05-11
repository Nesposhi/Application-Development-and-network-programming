"""Broadcasts readings to connected WebSocket clients."""
from __future__ import annotations

import asyncio
import json
from typing import Dict, Set


class Broadcaster:
    """Fan-out readings to WebSocket clients with optional per-client subscriptions."""

    def __init__(self):
        self._clients: Dict = {}  # ws -> set of subscribed sensor_ids

    async def register(self, websocket) -> None:
        """Register a new client (receives all sensors by default)."""
        self._clients[websocket] = set()

    async def unregister(self, websocket) -> None:
        """Unregister a disconnected client."""
        self._clients.pop(websocket, None)

    async def set_subscription(self, websocket, sensor_ids: Set[str]) -> None:
        """Update a client's subscription filter."""
        if websocket in self._clients:
            self._clients[websocket] = sensor_ids

    async def publish(self, reading: dict) -> None:
        """Broadcast a reading to interested clients."""
        try:
            message = json.dumps(reading)
        except Exception:
            return
        
        # Send to each interested client
        disconnected = []
        for ws, subscriptions in list(self._clients.items()):
            # Empty subscription = all sensors
            if not subscriptions or reading.get('sensor_id') in subscriptions:
                try:
                    await asyncio.wait_for(ws.send(message), timeout=1.0)
                except Exception:
                    disconnected.append(ws)
        
        # Clean up disconnected clients
        for ws in disconnected:
            self._clients.pop(ws, None)
