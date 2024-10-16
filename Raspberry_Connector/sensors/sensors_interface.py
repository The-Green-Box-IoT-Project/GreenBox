import json

from pathlib import Path

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


def retrieve_sensor(device_config):
    with open(device_config, 'r') as f:
        data = json.load(f)
        device_id = data['device_id']
        device_name = data['device_name']
        device_pin = data['pin']
        device_measurements = data['measurements']
    return device_id, device_name, device_pin, device_measurements


if __name__ == '__main__':
    pass
