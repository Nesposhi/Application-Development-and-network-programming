"""Entry point for the telemetry server.

Run with:
    python -m server

The server starts:
- TCP ingest server on 127.0.0.1:9000 for sensor connections
- HTTP REST API on 127.0.0.1:8080 for queries and dashboard

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

    # View dashboard:
    # Open http://127.0.0.1:8080/ in your browser
"""
from __future__ import annotations

import asyncio
import logging

from aiohttp import web

from .storage import Storage
from .tcp_ingest import start_tcp_server
from .rest_api import build_app

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


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

    logger.info("=" * 60)
    logger.info("Telemetry server started successfully!")
    logger.info("=" * 60)
    logger.info("TCP ingest server:  tcp://127.0.0.1:9000")
    logger.info("REST API:           http://127.0.0.1:8080")
    logger.info("Dashboard:          http://127.0.0.1:8080/")
    logger.info("Sensors endpoint:   http://127.0.0.1:8080/sensors")
    logger.info("=" * 60)

    try:
        # Run forever
        await asyncio.Future()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await runner.cleanup()
        tcp_server.close()
        await tcp_server.wait_closed()
        logger.info("Server shut down complete")


if __name__ == "__main__":
    asyncio.run(main())

