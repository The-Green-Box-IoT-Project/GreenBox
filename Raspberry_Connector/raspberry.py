import json

import requests
from pathlib import Path

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
CATALOG_FILE = P / 'catalog.json'


def retrieve_catalog():
    with open(CATALOG_FILE, 'r') as f:
        data = json.load(f)
        catalog_ip = data['catalog_ip']
        catalog_port = data['catalog_port']
        return catalog_ip, catalog_port


def retrieve_device():
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        device_id = data['device_id']
        device_name = data['device_name']
    return device_id, device_name


def retrieve_broker(catalog_ip, catalog_port):
    url = 'http://' + catalog_ip + ':' + str(catalog_port) + '/broker'
    broker_data = json.loads(requests.get(url).text)
    broker_ip = broker_data['broker_ip']
    broker_port = broker_data['broker_port']
    return broker_ip, int(broker_port)

def build_parent_topic(device_id):
    return f"""/greenhouse1/{device_id}"""


if __name__ == '__main__':
    pass
