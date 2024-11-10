"""
The purpose of this module is to generate and assign ids to devices that will be distributed, so that
each device is recognizable by the system at the moment of device registration, and to prevent unwanted external
devices to interfere with registered devices.
"""

import json
import uuid
from os import path
from pathlib import Path

P = Path(__file__).parent.absolute()
DEVICES_FILE = P / 'devices.json'
GREENHOUSES_FILE = P / 'greenhouses.json'


def init():
    if not path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'w') as f:
            f.write(json.dumps({}))
    if not path.exists(GREENHOUSES_FILE):
        with open(GREENHOUSES_FILE, 'w') as f:
            f.write(json.dumps({}))


def generate_id():
    """
    Generates an unique id to be assigned to a device.
    """
    out_id = str(uuid.uuid4())
    return out_id


def register_greenhouse(greenhouse_id):
    """
    Memorizes a newly created id, that is going to be assigned to a greenhouse.
    It will also be initialized the field for the owner, which is the user that will claim
    this greenhouse.
    """
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    greenhouses[greenhouse_id] = {
        'owner': None,
        'name': None
    }
    with open(GREENHOUSES_FILE, 'w') as f:
        f.write(json.dumps(greenhouses))


def register_device(device_id, device_type):
    """
    Memorizes a newly created id, that is going to be assigned to a device.
    It will also be initialized the field for the owner, which is the user that will claim
    this device.
    """
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    devices[device_id] = {
        'owner': None,
        'associated_greenhouse': None,
        'name': None,
        'device_type': device_type
    }
    with open(DEVICES_FILE, 'w') as f:
        f.write(json.dumps(devices))
