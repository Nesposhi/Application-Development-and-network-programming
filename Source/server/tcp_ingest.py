"""TCP ingest server for sensor connections."""
from __future__ import annotations

import asyncio
import logging
import struct

import sensor_pb2

logger = logging.getLogger(__name__)


async def handle_sensor(reader: asyncio.StreamReader, writer: asyncio.StreamWriter, storage):
    """Handle one sensor connection."""
    addr = writer.get_extra_info('peername')
    logger.info(f"Sensor connected from {addr}")
    
    try:
        while True:
            # Read 4-byte length
            length_bytes = await reader.readexactly(4)
            length = struct.unpack('>I', length_bytes)[0]
            
            if length > 1024 * 1024:
                logger.warning(f"Message too large: {length}")
                break
            
            # Read payload
            data = await reader.readexactly(length)
            
            try:
                reading = sensor_pb2.SensorReading()
                reading.ParseFromString(data)
                await storage.add_reading(reading)
                logger.debug(f"Stored reading from {reading.sensor_id}")
            except Exception as e:
                logger.warning(f"Parse error: {e}")
                
    except asyncio.IncompleteReadError:
        logger.info(f"Sensor {addr} disconnected")
    except Exception as e:
        logger.error(f"Error handling sensor: {e}")
    finally:
        writer.close()
        await writer.wait_closed()


async def start_tcp_server(host: str, port: int, storage) -> asyncio.AbstractServer:
    """Start TCP ingest server."""
    def handler(reader, writer):
        asyncio.create_task(handle_sensor(reader, writer, storage))
    
    server = await asyncio.start_server(handler, host, port)
    logger.info(f"TCP ingest listening on {host}:{port}")
    return server
