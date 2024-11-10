import json
from pathlib import Path

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


def load_sensor_attributes(device_config):
    with open(device_config, 'r') as f:
        data = json.load(f)
        device_id = data['device_id']
        device_name = data['device_name']
        device_pin = data['pin']
        device_measurements = data['measurements']
    return device_id, device_name, device_pin, device_measurements


def hardware_read(pin):
    raise NotImplementedError


class Sensor:
    def __init__(self, config_path):
        (self.device_id,
         self.device_name,
         self.device_pin,
         self.measurements) = load_sensor_attributes(config_path)

    def _build_topics(self, parent_topic):
        # todo: only one topic for dht11
        return (f"""{parent_topic}/{self.device_id}/{m['field']}""" for m in self.measurements)
