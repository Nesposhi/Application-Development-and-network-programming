"""WebSocket handler for /live endpoint."""
from __future__ import annotations

import asyncio
import json
from .broadcaster import Broadcaster


async def live(websocket, path: str, broadcaster: Broadcaster) -> None:
    """Handle WebSocket client connections."""
    await broadcaster.register(websocket)
    
    try:
        async for message in websocket:
            try:
                data = json.loads(message)
                if data.get('action') == 'subscribe':
                    sensors = set(data.get('sensors', []))
                    await broadcaster.set_subscription(websocket, sensors)
            except json.JSONDecodeError:
                pass
    finally:
        await broadcaster.unregister(websocket)
