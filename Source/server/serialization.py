"""Content negotiation for REST responses."""
from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from aiohttp import web
import yaml


def negotiate(request: web.Request) -> str:
    """Determine response format from Accept header."""
    accept = request.headers.get('Accept', 'application/json')
    
    if 'yaml' in accept.lower():
        return 'application/yaml'
    elif 'xml' in accept.lower():
        return 'application/xml'
    
    return 'application/json'


def serialize(data, media_type: str) -> bytes:
    """Serialize data to requested format."""
    if media_type == 'application/yaml':
        return yaml.dump(data).encode('utf-8')
    elif media_type == 'application/xml':
        return _to_xml(data).encode('utf-8')
    
    return json.dumps(data).encode('utf-8')


def _to_xml(data) -> str:
    """Convert data to simple XML."""
    def item_to_elem(tag, item):
        elem = ET.Element(tag)
        if isinstance(item, dict):
            for k, v in item.items():
                child = ET.SubElement(elem, k)
                child.text = str(v)
        else:
            elem.text = str(item)
        return elem
    
    if isinstance(data, list):
        root = ET.Element('items')
        for item in data:
            root.append(item_to_elem('item', item))
    else:
        root = item_to_elem('root', data)
    
    return ET.tostring(root, encoding='unicode')
