from pathlib import Path
import json

PARENT_PATH = Path(__file__).parent.absolute()
CONFIG = PARENT_PATH / 'config.json'


def retrieve_config():
    with open(CONFIG, 'r') as f:
        data = json.load(f)
        device_id = data['device_id']
        catalog_ip = data['catalog_ip']
        catalog_port = data['catalog_port']
        return device_id, catalog_ip, catalog_port
