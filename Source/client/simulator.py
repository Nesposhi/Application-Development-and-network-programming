"""Simple sensor simulator."""
from __future__ import annotations

import asyncio
import logging
import random
import struct
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from proto import telemetry_pb2
    USE_TELEMETRY = True
except ImportError:
    import sensor_pb2
    USE_TELEMETRY = False

logger = logging.getLogger(__name__)


class SensorSimulator:
    """Simulates one sensor sending readings to the server."""

    def __init__(self, sensor_id: str, sensor_type: str, interval_seconds: float,
                 host: str, port: int, value_range: tuple = (0, 100)):
        self.sensor_id = sensor_id
        self.sensor_type = sensor_type
        self.interval_seconds = interval_seconds
        self.host = host
        self.port = port
        self.value_range = value_range
        self._value = random.uniform(*value_range)

    async def run(self):
        """Connect and push readings forever."""
        while True:
            try:
                reader, writer = await asyncio.open_connection(self.host, self.port)
                logger.info(f"Sensor {self.sensor_id} connected")
                
                while True:
                    self._value += random.uniform(-5, 5)
                    self._value = max(self.value_range[0], 
                                     min(self.value_range[1], self._value))
                    
                    if USE_TELEMETRY:
                        reading = telemetry_pb2.Reading()
                        reading.sensor_id = self.sensor_id
                        reading.sensor_type = self.sensor_type
                    else:
                        reading = sensor_pb2.SensorReading()
                        reading.sensor_id = self.sensor_id
                    
                    reading.value = self._value
                    reading.timestamp = int(time.time() * 1000)
                    
                    data = reading.SerializeToString()
                    writer.write(struct.pack('>I', len(data)) + data)
                    await writer.drain()
                    await asyncio.sleep(self.interval_seconds)
                    
            except Exception as e:
                logger.error(f"Sensor {self.sensor_id}: {e}, retrying...")
                await asyncio.sleep(2)
