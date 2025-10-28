import json
import os
from pprint import pformat
from pathlib import Path

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class RaspberryConnector:
    CONFIG_PATH = P / 'config.json'

    def __init__(self):
        with open(self.CONFIG_PATH, 'r') as f:
            config = json.load(f)
        self.broker_ip = config['broker_ip']
        self.broker_port = config['broker_port']
        self.greenhouse_uuid = config['greenhouse_uuid']
        self.raspberry_uuid = config['raspberry_uuid']

        # TODO: le prossime due righe sono da cancellare dopo aver connesso il catalog
        self.greenhouse_uuid = os.getenv('GREENBOX_UUID')
        self.raspberry_uuid = os.getenv('RASPBERRY_UUID')

        self.time_interval = 5  # seconds
        self.topic = f"""/{self.greenhouse_uuid}/{self.raspberry_uuid}/sensors/"""

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)