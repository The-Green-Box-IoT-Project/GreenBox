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
    return _generate_token(username)


def _generate_token(username):
    with open(SESSIONS_FILE, 'r') as f:
        sessions = json.load(f)
    while True:
        token = str(uuid.uuid4())
        if token not in sessions:
            break
    clean_sessions = _expire_tokens(username)
    clean_sessions[token] = {'username': username}
    with open(SESSIONS_FILE, 'w') as f:
        f.write(json.dumps(clean_sessions))
    return token


def _expire_tokens(username):
    with open(SESSIONS_FILE, 'r') as f:
        sessions = json.load(f)
    clean_sessions = {k: v for k, v in sessions.items() if v['username'] != username}
    return clean_sessions


def validate_token(token):
    if token is None:
        return False
    with open(SESSIONS_FILE, 'r') as f:
        sessions = json.load(f)
        if token in sessions:
            return True
    return False


def retrieve_resources(token):
    if not validate_token(token):
        return None
    with open(SESSIONS_FILE, 'r') as f:
        username = json.load(f)[token]['username']
    with open(USERS_FILE, 'r') as f:
        rcs = json.load(f)[username]['resources']
    with open(RESOURCES_FILE, 'r') as f:
        rcs_ext = json.load(f)
        resource_catalog = [{rc: rcs_ext[rc]} for rc in rcs]
    return resource_catalog
