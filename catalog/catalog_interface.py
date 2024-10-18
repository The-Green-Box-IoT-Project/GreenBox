import json
from pathlib import Path
P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'

def retrieve_endpoint():
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        catalog_ip = data['catalog_ip']
        catalog_port = data['catalog_port']
    return catalog_ip, catalog_port