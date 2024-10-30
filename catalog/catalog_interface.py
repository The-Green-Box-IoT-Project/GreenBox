import json
import uuid
from pathlib import Path

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
USERS_FILE = P / 'users.json'
SESSIONS_FILE = P / 'sessions.json'
SERVICES_FILE = P / 'services.json'
RESOURCES_FILE = P / 'resources.json'


def retrieve_endpoint():
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        catalog_ip = data['catalog_ip']
        catalog_port = data['catalog_port']
    return catalog_ip, catalog_port


def retrieve_broker():
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        broker_ip = data['broker_ip']
        broker_port = data['broker_port']
    return broker_ip, broker_port


def validate_login(username, password):
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    if username not in users:
        return None
    if not users[username]['password'] == password:
        return None
    return _generate_token(username, password)


def _generate_token(username, password):
    with open(SESSIONS_FILE, 'r') as f:
        sessions = json.load(f)
    while True:
        token = str(uuid.uuid4())
        if token not in sessions:
            break
    sessions[token] = {'username': username, 'password': password}
    with open(SESSIONS_FILE, 'w') as f:
        f.write(json.dumps(sessions))
    return token


def validate_token(token):
    if token is None:
        return False
    with open(SESSIONS_FILE, 'r') as f:
        sessions = json.load(f)
        if token in sessions:
            return True
    return False
