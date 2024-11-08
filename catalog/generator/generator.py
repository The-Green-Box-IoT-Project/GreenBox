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


def generate_id(device_type):
    """
    Generates an unique id to be assigned to a device.
    """
    out_id = '%s_%s' % (device_type, uuid.uuid4())
    return out_id


def register_device(device_id):
    """
    Memorizes a newly created device id, ready to be assigned to a device.
    """
    if not path.exists(DEVICES_FILE):
        with open(DEVICES_FILE, 'w') as f:
            f.write(json.dumps({}))
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    devices[device_id] = {'associated': False}
    with open(DEVICES_FILE, 'w') as f:
        f.write(json.dumps(devices))


if __name__ == '__main__':
    new_id = generate_id('dht11')
    print(f'Generated id: {new_id}')
    register_device(new_id)
    print(f'Registered device: {new_id}')
