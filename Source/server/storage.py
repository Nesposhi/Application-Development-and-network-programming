"""Simple SQLite storage for sensors and readings."""
from __future__ import annotations

import sqlite3
from typing import Iterable, Optional


class Storage:
    """SQLite-based storage for sensor readings."""

    def __init__(self, db_path: str = ":memory:"):
        self.db_path = db_path
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._init_db()

    def _init_db(self):
        """Initialize the database tables."""
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS sensors (
                id TEXT PRIMARY KEY,
                type TEXT NOT NULL
            )
        """)
        self._conn.execute("""
            CREATE TABLE IF NOT EXISTS readings (
                sensor_id TEXT,
                timestamp INTEGER,
                value REAL,
                type TEXT
            )
        """)
        self._conn.commit()

    async def init(self):
        """Async initialization hook (no-op)."""
        pass

    async def add_sensor(self, sensor: dict) -> None:
        """Register a new sensor."""
        self._conn.execute(
            "INSERT OR IGNORE INTO sensors (id, type) VALUES (?, ?)",
            (sensor['id'], sensor['type'])
        )
        self._conn.commit()

    async def remove_sensor(self, sensor_id: str) -> None:
        """Remove a sensor and its readings."""
        self._conn.execute("DELETE FROM readings WHERE sensor_id = ?", (sensor_id,))
        self._conn.execute("DELETE FROM sensors WHERE id = ?", (sensor_id,))
        self._conn.commit()

    async def list_sensors(self) -> Iterable[dict]:
        """Return all registered sensors."""
        cursor = self._conn.execute("SELECT id, type FROM sensors")
        return [{'id': row[0], 'type': row[1]} for row in cursor.fetchall()]

    async def add_reading(self, reading) -> None:
        """Store a reading and auto-register the sensor."""
        sensor_id = reading.sensor_id
        value = reading.value
        timestamp = reading.timestamp
        sensor_type = getattr(reading, 'sensor_type', 'unknown')
        
        # Auto-register sensor if not present
        self._conn.execute(
            "INSERT OR IGNORE INTO sensors (id, type) VALUES (?, ?)",
            (sensor_id, sensor_type)
        )
        
        # Store reading
        self._conn.execute(
            "INSERT INTO readings (sensor_id, timestamp, value, type) VALUES (?, ?, ?, ?)",
            (sensor_id, timestamp, value, sensor_type)
        )
        self._conn.commit()

    async def get_readings(
        self,
        sensor_id: str,
        from_ts: Optional[float] = None,
        to_ts: Optional[float] = None,
    ) -> Iterable[dict]:
        """Fetch readings for a sensor within optional time window."""
        query = "SELECT timestamp, value, type FROM readings WHERE sensor_id = ?"
        params = [sensor_id]
        
        if from_ts is not None:
            query += " AND timestamp >= ?"
            params.append(int(from_ts))
        if to_ts is not None:
            query += " AND timestamp <= ?"
            params.append(int(to_ts))
        
        query += " ORDER BY timestamp"
        cursor = self._conn.execute(query, params)
        return [{'timestamp': row[0], 'value': row[1], 'type': row[2]} 
                for row in cursor.fetchall()]
