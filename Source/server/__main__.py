"""Entry point for the telemetry server.

Run with:
    python -m server

The server starts:
- TCP ingest server on 127.0.0.1:9000 for sensor connections
- HTTP REST API on 127.0.0.1:8080 for queries
- WebSocket live feed on ws://127.0.0.1:8080/live

Usage Examples:
    # Start the server
    python -m server

    # In another terminal, test REST API:
    curl http://127.0.0.1:8080/sensors
    curl "http://127.0.0.1:8080/sensors/temp_1/readings?from=1640995200000"

    # Register a sensor:
    curl -X POST http://127.0.0.1:8080/sensors \
      -H "Content-Type: application/json" \
      -d '{"id": "new_sensor", "type": "pressure"}'

    # WebSocket live feed (connect with a WebSocket client):
    # ws://127.0.0.1:8080/live
    # Send: {"subscribe": ["temp_1"]} to filter readings
"""
from __future__ import annotations

import asyncio
import logging

from aiohttp import web

from .storage import Storage
from .tcp_ingest import start_tcp_server
from .rest_api import build_app

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Boot the telemetry server.

    Responsibilities:
      - Initialise the storage layer.
      - Start the TCP ingest listener for sensor connections.
      - Start the aiohttp app hosting the REST API.
      - Wait until shutdown.
    """
    storage = Storage('telemetry.db')
    await storage.init()

    # Start TCP server
    tcp_server = await start_tcp_server('127.0.0.1', 9000, storage)

    # Start aiohttp app
    app = build_app(storage)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '127.0.0.1', 8080)
    await site.start()

    logging.info("Telemetry server started: TCP on 127.0.0.1:9000, HTTP on 127.0.0.1:8080")

    try:
        # Run forever
        await asyncio.Future()  # Wait indefinitely
    except KeyboardInterrupt:
        logging.info("Shutting down...")
    finally:
        await runner.cleanup()
        tcp_server.close()
        await tcp_server.wait_closed()


if __name__ == "__main__":
    asyncio.run(main())
