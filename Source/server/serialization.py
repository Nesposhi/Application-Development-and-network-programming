"""Content negotiation for the REST API.

Maps the `Accept` header on a request to a serializer for the response.
Supported media types:
    application/json
    application/xml
    application/yaml   (also accepts text/yaml)

Falls back to JSON when no supported type matches.
"""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from typing import Any

import yaml
from aiohttp import web


def negotiate(request: web.Request) -> str:
    """Return the chosen response media type for `request`."""
    accept = request.headers.get('Accept', 'application/json')
    # Simple parsing, prefer json, then yaml, then xml
    if 'application/json' in accept:
        return 'application/json'
    elif 'application/yaml' in accept or 'text/yaml' in accept:
        return 'application/yaml'
    elif 'application/xml' in accept:
        return 'application/xml'
    else:
        return 'application/json'  # Default fallback

def serialize(payload: Any, media_type: str) -> bytes:
    """Serialize `payload` (a dict or list of dicts) into bytes."""
    if media_type == 'application/json':
        return json.dumps(payload).encode('utf-8')
    elif media_type == 'application/yaml':
        return yaml.dump(payload).encode('utf-8')
    elif media_type == 'application/xml':
        return _to_xml(payload).encode('utf-8')
    else:
        return json.dumps(payload).encode('utf-8')

def _to_xml(data: Any) -> str:
    """Convert dict/list to XML string."""
    def dict_to_xml(tag, d):
        elem = ET.Element(tag)
        for key, val in d.items():
            child = ET.SubElement(elem, key)
            child.text = str(val)
        return elem

    if isinstance(data, list):
        root = ET.Element('items')
        for item in data:
            if isinstance(item, dict):
                root.append(dict_to_xml('item', item))
        return ET.tostring(root, encoding='unicode')
    elif isinstance(data, dict):
        root = dict_to_xml('root', data)
        return ET.tostring(root, encoding='unicode')
    else:
        return str(data)
