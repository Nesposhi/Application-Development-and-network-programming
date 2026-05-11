"""WebSocket server for live readings."""
from __future__ import annotations

import asyncio
import logging

from websockets import serve

from .broadcaster import Broadcaster
from .handler import live
from server.storage import Storage

logging.basicConfig(level=logging.INFO)


async def poll_db(storage: Storage, broadcaster: Broadcaster):
    """Poll database for new readings and broadcast them."""
    last_ts = 0
    
    while True:
        try:
            cursor = storage._conn.execute(
                "SELECT sensor_id, type, timestamp, value FROM readings "
                "WHERE timestamp > ? ORDER BY timestamp",
                (last_ts,)
            )
            
            for row in cursor.fetchall():
                reading = {
                    'sensor_id': row[0],
                    'type': row[1],
                    'timestamp': row[2],
                    'value': row[3]
                }
                await broadcaster.publish(reading)
                last_ts = row[2]
        except Exception:
            pass
        
        await asyncio.sleep(1)


async def main():
    """Start WebSocket server."""
    broadcaster = Broadcaster()
    storage = Storage('telemetry.db')
    await storage.init()
    
    # Start polling
    asyncio.create_task(poll_db(storage, broadcaster))
    
    # Start WebSocket server
    logging.info("WebSocket server starting on ws://127.0.0.1:8081/live")
    server = await serve(lambda ws, path: live(ws, path, broadcaster), 
                        "127.0.0.1", 8081)
    await server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
