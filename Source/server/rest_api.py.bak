"""REST API for the telemetry server.

Endpoints:
    GET    /sensors                       list registered sensors
    GET    /sensors/{id}/readings         historical readings  (?from=&to=)
    POST   /sensors                       register a new sensor
    DELETE /sensors/{id}                  remove a sensor
    WS     /live                          live readings via WebSocket

Content negotiation:
    Server-driven via the `Accept` header. Supported media types:
      application/json, application/xml, application/yaml.
    Delegates to server.serialization.

Sessions:
    Simplified: no cookies for now.
"""
from __future__ import annotations

import json
from aiohttp import web, WSMsgType
from .serialization import negotiate, serialize
from .tcp_ingest import broadcaster


async def list_sensors(request: web.Request) -> web.Response:
    """GET /sensors — list all registered sensors.

    Example: curl http://127.0.0.1:8080/sensors
    Returns: [{"id": "temp_1", "type": "temperature"}, ...]
    """
    storage = request.app['storage']
    sensors = await storage.list_sensors()
    media_type = negotiate(request)
    data = list(sensors)
    return web.Response(
        body=serialize(data, media_type),
        content_type=media_type,
        headers={'Content-Type': media_type}
    )


async def get_readings(request: web.Request) -> web.Response:
    """GET /sensors/{id}/readings — historical readings for a sensor.

    Query params: from (timestamp ms), to (timestamp ms)

    Example: curl "http://127.0.0.1:8080/sensors/temp_1/readings?from=1640995200000"
    Returns: [{"timestamp": 1640995200000, "value": 25.5}, ...]
    """
    sensor_id = request.match_info['id']
    from_ts = request.query.get('from')
    to_ts = request.query.get('to')
    if from_ts:
        from_ts = float(from_ts)
    if to_ts:
        to_ts = float(to_ts)
    storage = request.app['storage']
    readings = await storage.get_readings(sensor_id, from_ts, to_ts)
    media_type = negotiate(request)
    data = list(readings)
    return web.Response(
        body=serialize(data, media_type),
        content_type=media_type,
        headers={'Content-Type': media_type}
    )


async def register_sensor(request: web.Request) -> web.Response:
    """POST /sensors — register a new sensor.

    Body: {"id": "sensor_id", "type": "sensor_type"}

    Example: curl -X POST http://127.0.0.1:8080/sensors \
             -H "Content-Type: application/json" \
             -d '{"id": "pressure_1", "type": "pressure"}'
    Returns: 201 Created
    """
    data = await request.json()
    sensor = {'id': data['id'], 'type': data['type']}
    storage = request.app['storage']
    await storage.add_sensor(sensor)
    return web.Response(status=201, headers={'Location': f'/sensors/{sensor["id"]}'}, text='Created')


async def delete_sensor(request: web.Request) -> web.Response:
    """DELETE /sensors/{id} — remove a sensor.

    Example: curl -X DELETE http://127.0.0.1:8080/sensors/pressure_1
    Returns: 204 No Content
    """
    sensor_id = request.match_info['id']
    storage = request.app['storage']
    await storage.remove_sensor(sensor_id)
    return web.Response(status=204)


async def dashboard(request: web.Request) -> web.Response:
    """Serve the dashboard HTML page."""
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Sensor Dashboard</title>
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            margin: 0;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            padding: 30px;
            margin-top: 20px;
        }
        h1 {
            text-align: center;
            color: #2c3e50;
            margin-bottom: 30px;
            font-weight: 300;
        }
        .status {
            text-align: center;
            margin: 20px 0;
            padding: 10px;
            border-radius: 5px;
            font-weight: bold;
            font-size: 16px;
        }
        .status.connected {
            background-color: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
        .status.disconnected {
            background-color: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .controls {
            text-align: center;
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 8px;
            border: 1px solid #e9ecef;
        }
        .controls label {
            font-weight: bold;
            margin-right: 10px;
            color: #495057;
        }
        select {
            padding: 8px 12px;
            border: 1px solid #ced4da;
            border-radius: 4px;
            background: white;
            min-width: 200px;
            margin-right: 10px;
        }
        button {
            padding: 8px 16px;
            background: #007bff;
            color: white;
            border: none;
            border-radius: 4px;
            cursor: pointer;
            font-weight: bold;
            transition: background-color 0.2s;
        }
        button:hover {
            background: #0056b3;
        }
        .chart-container {
            width: 100%;
            margin: 30px auto;
            padding: 20px;
            background: white;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.05);
        }
        .info {
            text-align: center;
            margin-top: 20px;
            color: #6c757d;
            font-size: 14px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🌤️ Sensor Weather Station</h1>
        <div class="status" id="status">🔄 Connecting...</div>
    </div>

    <div class="controls">
        <label for="sensor-select">📡 Monitor Sensors:</label>
        <select id="sensor-select" multiple>
            <option value="">🌍 All Sensors</option>
        </select>
        <button onclick="updateSubscription()">🔄 Update</button>
    </div>

    <div class="dashboard" id="dashboard">
        <div class="loading">Loading sensors...</div>
    </div>

    <script>
        const statusDiv = document.getElementById('status');
        const dashboardDiv = document.getElementById('dashboard');
        const sensorSelect = document.getElementById('sensor-select');

        let ws;
        let sensorData = {};
        let subscribedSensors = new Set();

        // Sensor type configurations
        const sensorConfig = {
            temperature: { unit: '°C', icon: '🌡️', color: '#ff6b6b' },
            humidity: { unit: '%', icon: '💧', color: '#4ecdc4' },
            soil_moisture: { unit: '%', icon: '🌱', color: '#45b7d1' },
            pressure: { unit: 'hPa', icon: '📊', color: '#96ceb4' },
            light: { unit: 'lux', icon: '☀️', color: '#ffeaa7' }
        };

        // Connect to WebSocket
        function connect() {
            ws = new WebSocket('ws://' + window.location.host + '/live');

            ws.onopen = function() {
                statusDiv.textContent = '✅ Connected';
                statusDiv.className = 'status connected';
            };

            ws.onmessage = function(event) {
                const reading = JSON.parse(event.data);
                updateSensorData(reading);
            };

            ws.onclose = function() {
                statusDiv.textContent = '❌ Disconnected - Reconnecting...';
                statusDiv.className = 'status disconnected';
                setTimeout(connect, 1000);
            };

            ws.onerror = function(error) {
                statusDiv.textContent = '⚠️ Error: ' + error;
                statusDiv.className = 'status disconnected';
            };
        }

        // Update sensor data and UI
        function updateSensorData(reading) {
            const sensorId = reading.sensor_id;
            const value = reading.value;
            const timestamp = new Date(reading.timestamp);

            if (!sensorData[sensorId]) {
                sensorData[sensorId] = { values: [], lastUpdate: timestamp };
            }

            sensorData[sensorId].values.push({ value, timestamp });
            sensorData[sensorId].lastUpdate = timestamp;

            // Keep only last 10 values for trend calculation
            if (sensorData[sensorId].values.length > 10) {
                sensorData[sensorId].values.shift();
            }

            updateSensorCard(sensorId);
        }

        // Create or update sensor card
        function updateSensorCard(sensorId) {
            let card = document.getElementById(`sensor-${sensorId}`);
            const data = sensorData[sensorId];
            const latest = data.values[data.values.length - 1];

            if (!card) {
                card = createSensorCard(sensorId);
                dashboardDiv.appendChild(card);
            }

            const config = sensorConfig[data.type] || sensorConfig.temperature;
            const trend = calculateTrend(data.values);
            const trendClass = trend > 0 ? 'trend-up' : trend < 0 ? 'trend-down' : 'trend-stable';
            const trendIcon = trend > 0 ? '📈' : trend < 0 ? '📉' : '➡️';

            card.querySelector('.sensor-value').textContent = latest.value.toFixed(1);
            card.querySelector('.sensor-unit').textContent = config.unit;
            card.querySelector('.trend-icon').textContent = trendIcon;
            card.querySelector('.trend-icon').className = `trend-icon ${trendClass}`;
            card.querySelector('.last-update').textContent = `Updated: ${data.lastUpdate.toLocaleTimeString()}`;
        }

        // Create sensor card
        function createSensorCard(sensorId) {
            const data = sensorData[sensorId];
            const config = sensorConfig[data.type] || sensorConfig.temperature;

            const card = document.createElement('div');
            card.className = 'sensor-card';
            card.id = `sensor-${sensorId}`;

            card.innerHTML = `
                <div class="sensor-header">
                    <div class="sensor-name">${config.icon} ${sensorId}</div>
                    <div class="sensor-type">${data.type || 'unknown'}</div>
                </div>
                <div class="sensor-value">0<span class="sensor-unit">${config.unit}</span></div>
                <div class="sensor-trend">
                    <span class="trend-icon trend-stable">➡️</span>
                    <span>Stable</span>
                </div>
                <div class="last-update">Loading...</div>
            `;

            return card;
        }

        // Calculate trend (simple: compare first and last values)
        function calculateTrend(values) {
            if (values.length < 2) return 0;
            const first = values[0].value;
            const last = values[values.length - 1].value;
            return last - first;
        }

        // Update subscription
        function updateSubscription() {
            const selected = Array.from(sensorSelect.selectedOptions).map(option => option.value).filter(v => v);
            subscribedSensors = new Set(selected);

            if (selected.length === 0) {
                ws.send(JSON.stringify({ subscribe: [] }));
            } else {
                ws.send(JSON.stringify({ subscribe: selected }));
            }
        }

        // Load available sensors
        async function loadSensors() {
            try {
                const response = await fetch('/sensors');
                const sensors = await response.json();

                // Initialize sensor data
                sensors.forEach(sensor => {
                    sensorData[sensor.id] = {
                        type: sensor.type,
                        values: [],
                        lastUpdate: new Date()
                    };
                });

                // Update selector
                sensorSelect.innerHTML = '<option value="">🌍 All Sensors</option>';
                sensors.forEach(sensor => {
                    const option = document.createElement('option');
                    option.value = sensor.id;
                    option.textContent = `${sensorConfig[sensor.type]?.icon || '📊'} ${sensor.id}`;
                    sensorSelect.appendChild(option);
                });

                // Create initial cards
                dashboardDiv.innerHTML = '';
                sensors.forEach(sensor => {
                    const card = createSensorCard(sensor.id);
                    dashboardDiv.appendChild(card);
                });

            } catch (error) {
                console.error('Failed to load sensors:', error);
                dashboardDiv.innerHTML = '<div class="loading">Failed to load sensors</div>';
            }
        }

        // Initialize
        connect();
        loadSensors();
    </script>
</body>

    <script>
        const statusDiv = document.getElementById('status');
        const sensorSelect = document.getElementById('sensor-select');
        const ctx = document.getElementById('sensorChart').getContext('2d');

        let ws;
        let sensorData = {};
        let chart;

        // Initialize chart
        function initChart() {
            chart = new Chart(ctx, {
                type: 'line',
                data: {
                    datasets: []
                },
                options: {
                    responsive: true,
                    scales: {
                        x: {
                            type: 'time',
                            time: {
                                unit: 'second'
                            }
                        },
                        y: {
                            beginAtZero: false
                        }
                    }
                }
            });
        }

        // Connect to WebSocket
        function connect() {
            ws = new WebSocket('ws://' + window.location.host + '/live');

            ws.onopen = function() {
                statusDiv.textContent = '✅ Connected';
                statusDiv.className = 'status connected';
            };

            ws.onmessage = function(event) {
                const reading = JSON.parse(event.data);
                updateData(reading);
            };

            ws.onclose = function() {
                statusDiv.textContent = '❌ Disconnected - Reconnecting...';
                statusDiv.className = 'status disconnected';
                setTimeout(connect, 1000);
            };

            ws.onerror = function(error) {
                statusDiv.textContent = '⚠️ Error: ' + error;
                statusDiv.className = 'status disconnected';
            };
        }

        // Update data and chart
        function updateData(reading) {
            const sensorId = reading.sensor_id;
            const timestamp = new Date(reading.timestamp);
            const value = reading.value;

            if (!sensorData[sensorId]) {
                sensorData[sensorId] = [];
                addDataset(sensorId);
            }

            sensorData[sensorId].push({ x: timestamp, y: value });

            // Keep only last 50 points
            if (sensorData[sensorId].length > 50) {
                sensorData[sensorId].shift();
            }

            updateChart(sensorId);
        }

        // Add dataset to chart
        function addDataset(sensorId) {
            const colors = ['red', 'blue', 'green', 'orange', 'purple', 'brown'];
            const color = colors[chart.data.datasets.length % colors.length];

            chart.data.datasets.push({
                label: sensorId,
                data: sensorData[sensorId],
                borderColor: color,
                backgroundColor: color,
                fill: false,
                tension: 0.1
            });
            chart.update();
        }

        // Update chart data
        function updateChart(sensorId) {
            const dataset = chart.data.datasets.find(ds => ds.label === sensorId);
            if (dataset) {
                dataset.data = sensorData[sensorId];
                chart.update();
            }
        }

        // Update subscription
        function updateSubscription() {
            const selected = Array.from(sensorSelect.selectedOptions).map(option => option.value).filter(v => v);
            if (selected.length === 0) {
                // Subscribe to all (empty array)
                ws.send(JSON.stringify({ subscribe: [] }));
            } else {
                ws.send(JSON.stringify({ subscribe: selected }));
            }
        }

        // Load available sensors
        async function loadSensors() {
            try {
                const response = await fetch('/sensors');
                const sensors = await response.json();
                sensorSelect.innerHTML = '<option value="">All Sensors</option>';
                sensors.forEach(sensor => {
                    const option = document.createElement('option');
                    option.value = sensor.id;
                    option.textContent = `${sensor.id} (${sensor.type})`;
                    sensorSelect.appendChild(option);
                });
            } catch (error) {
                console.error('Failed to load sensors:', error);
            }
        }

        // Initialize
        initChart();
        connect();
        loadSensors();
    </script>
</body>
</html>"""
    return web.Response(text=html_content, content_type='text/html')


async def live_readings(request: web.Request) -> web.WebSocketResponse:
    """WebSocket /live — stream live readings with optional sensor subscriptions.

    Connect: ws://127.0.0.1:8080/live
    Subscribe: Send {"subscribe": ["sensor1", "sensor2"]}
    Receives: {"sensor_id": "temp_1", "value": 25.5, "timestamp": 1640995200000}
    """
    ws = web.WebSocketResponse()
    await ws.prepare(request)

    broadcaster.add_client(ws, set())  # Start with no subscriptions (receives all)
    try:
        async for msg in ws:
            if msg.type == WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    if 'subscribe' in data and isinstance(data['subscribe'], list):
                        broadcaster.update_subscriptions(ws, set(data['subscribe']))
                except Exception:
                    pass  # Ignore invalid messages
            elif msg.type == WSMsgType.ERROR:
                break
    finally:
        broadcaster.remove_client(ws)

    return ws


def build_app(storage) -> web.Application:
    """Build the aiohttp application."""
    app = web.Application()
    app['storage'] = storage
    app.router.add_get('/sensors', list_sensors)
    app.router.add_get('/sensors/{id}/readings', get_readings)
    app.router.add_post('/sensors', register_sensor)
    app.router.add_delete('/sensors/{id}', delete_sensor)
    app.router.add_get('/live', live_readings)
    app.router.add_get('/dashboard', dashboard)
    return app
    raise NotImplementedError
