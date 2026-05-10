"""Single-sensor simulation logic.

Each simulated sensor:
  - Connects to the telemetry server over TCP.
  - Generates plausible readings on its configured interval.
  - Encodes each reading as a Protobuf message and writes a length-prefixed
    frame on the socket.
  - Reconnects with backoff after transient network failures.
"""
from __future__ import annotations

import asyncio
import logging
import random
import struct
import time
from typing import Optional

import sensor_pb2

logger = logging.getLogger(__name__)


class SensorSimulator:
    """Simulates one sensor pushing readings to the telemetry server.

    Connects to server at host:port, sends Protobuf-encoded readings
    with length-prefixed framing every interval_seconds.
    """

    def __init__(
        self,
        sensor_id: str,
        sensor_type: str,
        interval_seconds: float,
        host: str,
        port: int,
        value_range: Optional[tuple[float, float]] = None,
    ) -> None:
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.interval_seconds = interval_seconds
        self.host = host
        self.port = port
        self.value_range = value_range or (0, 100)
        self._last_value = random.uniform(*self.value_range)

    async def run(self) -> None:
        """Connect, then push readings on the configured interval forever."""
        backoff = 1.0
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                logger.info(f"Sensor {self.sensor_id} connected to {self.host}:{self.port}")
                backoff = 1.0  # reset backoff on success
                while True:
                    reading = self._generate_reading()
                    data = reading.SerializeToString()
                    # Length-prefixed: 4 bytes big-endian length
                    frame = struct.pack('>I', len(data)) + data
                    writer.write(frame)
                    await writer.drain()
                    logger.debug(f"Sent reading: {reading}")
                    await asyncio.sleep(self.interval_seconds)
            except (OSError, asyncio.TimeoutError) as e:
                logger.warning(f"Sensor {self.sensor_id} connection failed: {e}, retrying in {backoff}s")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, 60)  # exponential backoff, max 60s
            except Exception as e:
                logger.error(f"Unexpected error for sensor {self.sensor_id}: {e}")
                await asyncio.sleep(5)

    def _generate_reading(self) -> sensor_pb2.SensorReading:
        """Produce a plausible next Reading for this sensor."""
        # Simple random walk within range
        delta = random.uniform(-5, 5)
        self._last_value = max(self.value_range[0], min(self.value_range[1], self._last_value + delta))
        reading = sensor_pb2.SensorReading()
        reading.sensor_id = self.sensor_id
        reading.value = self._last_value
        reading.timestamp = int(time.time() * 1000)  # milliseconds
        return reading
