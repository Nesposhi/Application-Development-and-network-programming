"""Entry point for the sensor simulator.

Run with:
    python -m client --config config/sensors.yaml

Usage Examples:
    # Start simulator with default config
    python -m client

    # Use custom config file
    python -m client --config path/to/custom_config.yaml

    # Config file should contain server host/port and sensor definitions:
    # server:
    #   host: 127.0.0.1
    #   port: 9000
    # sensors:
    #   - id: temp_1
    #     type: temperature
    #     interval_seconds: 5
    #     range: [20, 30]
"""
from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

import yaml

from .simulator import SensorSimulator

logging.basicConfig(level=logging.INFO)


async def main() -> None:
    """Load the YAML config, spawn one task per sensor, run them all."""
    parser = argparse.ArgumentParser(description="Sensor Simulator")
    parser.add_argument("--config", type=Path, default=Path("config/sensors.yaml"), help="Path to YAML config file")
    args = parser.parse_args()

    if not args.config.exists():
        print(f"Config file {args.config} not found", file=sys.stderr)
        sys.exit(1)

    with open(args.config) as f:
        config = yaml.safe_load(f)

    server_config = config.get("server", {})
    host = server_config.get("host", "127.0.0.1")
    port = server_config.get("port", 9000)

    sensors_config = config.get("sensors", [])
    if not sensors_config:
        print("No sensors defined in config", file=sys.stderr)
        sys.exit(1)

    tasks = []
    for sensor in sensors_config:
        sensor_id = sensor["id"]
        sensor_type = sensor["type"]
        interval = sensor["interval_seconds"]
        value_range = tuple(sensor.get("range", [0, 100]))
        sim = SensorSimulator(sensor_id, sensor_type, interval, host, port, value_range)
        task = asyncio.create_task(sim.run())
        tasks.append(task)

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    asyncio.run(main())
