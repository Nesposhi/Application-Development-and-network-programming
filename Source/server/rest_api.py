"""Simple REST API for the telemetry server."""
from __future__ import annotations

import uuid
from aiohttp import web
from .serialization import negotiate, serialize


async def list_sensors(request: web.Request) -> web.Response:
    """GET /sensors — list registered sensors."""
    storage = request.app['storage']
    sensors = await storage.list_sensors()
    media_type = negotiate(request)
    return web.Response(
        body=serialize(list(sensors), media_type),
        content_type=media_type
    )


async def get_readings(request: web.Request) -> web.Response:
    """GET /sensors/{id}/readings — historical readings."""
    sensor_id = request.match_info['id']
    from_ts = request.query.get('from')
    to_ts = request.query.get('to')
    
    storage = request.app['storage']
    readings = await storage.get_readings(
        sensor_id,
        float(from_ts) if from_ts else None,
        float(to_ts) if to_ts else None
    )
    media_type = negotiate(request)
    return web.Response(
        body=serialize(list(readings), media_type),
        content_type=media_type
    )


async def register_sensor(request: web.Request) -> web.Response:
    """POST /sensors — register a new sensor."""
    data = await request.json()
    sensor = {'id': data['id'], 'type': data['type']}
    storage = request.app['storage']
    await storage.add_sensor(sensor)
    return web.Response(status=201, text='Created')


async def delete_sensor(request: web.Request) -> web.Response:
    """DELETE /sensors/{id} — remove a sensor."""
    sensor_id = request.match_info['id']
    storage = request.app['storage']
    await storage.remove_sensor(sensor_id)
    return web.Response(status=204)


async def dashboard(request: web.Request) -> web.Response:
    """Serve the dashboard HTML."""
    try:
        with open('dashboard.html', 'r') as f:
            html = f.read()
    except FileNotFoundError:
        html = '<h1>Dashboard not available</h1>'
    
    resp = web.Response(text=html, content_type='text/html')
    resp.set_cookie('session_id', str(uuid.uuid4()), max_age=86400)
    return resp


def build_app(storage) -> web.Application:
    """Build the aiohttp application."""
    app = web.Application()
    app['storage'] = storage
    
    app.router.add_get('/', dashboard)
    app.router.add_get('/sensors', list_sensors)
    app.router.add_post('/sensors', register_sensor)
    app.router.add_get('/sensors/{id}/readings', get_readings)
    app.router.add_delete('/sensors/{id}', delete_sensor)
    
    return app
