"""Asynchronous TCP listener for sensor connections.

Sensors connect over TCP and stream Protobuf-encoded readings. This module:
  - Accepts connections concurrently with asyncio.start_server.
  - Frames and decodes each Protobuf message from the byte stream.
  - Hands decoded readings to the storage layer (and optionally to a
    broadcaster so the WebSocket /live feed can push them).
  - Tolerates disconnects and malformed messages without crashing the server.

Framing convention: 4-byte big-endian length prefix followed by the Protobuf
payload of that length. Adjust if your design uses a different framing scheme.
"""
from __future__ import annotations

import asyncio
import logging
import struct
from typing import Callable

import sensor_pb2

logger = logging.getLogger(__name__)


class Broadcaster:
    """Broadcasts readings to WebSocket clients."""

    def __init__(self):
        self._clients = {}  # ws -> set of subscribed sensor_ids

    def add_client(self, ws, subscriptions=None):
        if subscriptions is None:
            subscriptions = set()
        self._clients[ws] = subscriptions

    def remove_client(self, ws):
        self._clients.pop(ws, None)

    def update_subscriptions(self, ws, subscriptions):
        if ws in self._clients:
            self._clients[ws].update(subscriptions)

    async def broadcast(self, reading):
        """Broadcast a reading to all connected clients."""
        message = {
            'sensor_id': reading.sensor_id,
            'value': reading.value,
            'timestamp': reading.timestamp
        }
        for ws, subs in list(self._clients.items()):
            if not subs or reading.sensor_id in subs:
                try:
                    await ws.send_json(message)
                except Exception:
                    self._clients.pop(ws, None)


broadcaster = Broadcaster()


async def handle_sensor(
    reader: asyncio.StreamReader,
    writer: asyncio.StreamWriter,
    storage,
) -> None:
    """Handle one sensor connection until it closes."""
    addr = writer.get_extra_info('peername')
    logger.info(f"Sensor connected from {addr}")
    try:
        while True:
            # Read 4-byte length prefix
            length_bytes = await reader.readexactly(4)
            length = struct.unpack('>I', length_bytes)[0]
            if length > 1024 * 1024:  # 1MB limit
                logger.warning(f"Message too large: {length}")
                break
            # Read the Protobuf payload
            data = await reader.readexactly(length)
            try:
                reading = sensor_pb2.SensorReading()
                reading.ParseFromString(data)
                logger.debug(f"Received reading: {reading}")
                await storage.add_reading(reading)
                await broadcaster.broadcast(reading)
            except Exception as e:
                logger.warning(f"Failed to parse message: {e}")
                # Continue, don't drop connection
    except asyncio.IncompleteReadError:
        logger.info(f"Sensor {addr} disconnected")
    except Exception as e:
        logger.error(f"Error handling sensor {addr}: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_tcp_server(host: str, port: int, storage) -> asyncio.AbstractServer:
    """Start the TCP ingest server listening on (host, port)."""
    def handler(reader, writer):
        asyncio.create_task(handle_sensor(reader, writer, storage))

    server = await asyncio.start_server(handler, host, port)
    logger.info(f"TCP ingest server listening on {host}:{port}")
    return server
