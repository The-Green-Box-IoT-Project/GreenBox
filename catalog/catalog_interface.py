import json
from os import path
from pathlib import Path
from pprint import pprint
from Adapters.mongo.Mongo_DB_adapter import MongoAdapter
import os
import requests

from .auth_token import Token

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
USERS_FILE = P / 'users.json'
SERVICES_FILE = P / 'services.json'
GREENHOUSES_FILE = P / 'generator' / 'greenhouses.json'
DEVICES_FILE = P / 'generator' / 'devices.json'
DEVICES_LEGEND_FILE = P / 'devices_legend.json'
ROOT_DIR = P.parent
STRATEGIES_FILE = ROOT_DIR / 'Control_Strategies' / 'strategies.json'
CROP_PROFILES_FILE = ROOT_DIR / 'Control_Strategies' / 'crop_profiles.json'
MONGO_ADAPTER_URL = os.getenv("MONGO_ADAPTER_URL", "http://127.0.0.1:8082")


def init():
    catalogs = [USERS_FILE, SERVICES_FILE,
                GREENHOUSES_FILE, DEVICES_FILE,
                STRATEGIES_FILE, CROP_PROFILES_FILE]
    for catalog in catalogs:
        if not path.exists(catalog):
            with open(catalog, 'w') as f:
                f.write(json.dumps({}))


def retrieve_broker():
    """
    Used to retrieve ip and port of the broker
    """
    with open(CONFIG_FILE, 'r') as f:
        data = json.load(f)
        broker_ip = data['broker_ip']
        broker_port = data['broker_port']
    return broker_ip, broker_port


def signup_user(username, password):
    """
    Used to register a new user into the system.
    """
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    if username in users:
        return False
    users[username] = {
        'password': password,
        'greenhouses': []
    }
    with open(USERS_FILE, 'w') as f:
        f.write(json.dumps(users))
    return True


def validate_login(username, password):
    """
    Used to validate login credentials and give a session token to the
    user.
    """
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    if username not in users:
        return None
    if not users[username]['password'] == password:
        return None
    token = Token.generate(username)
    return Token.serialize(token)


def verify_token(token_http):
    """
    Used to verify the validity of a specific session token.
    """
    if token_http is None:
        return False
    return not Token.deserialize(token_http).is_expired()


def retrieve_username_by_token(token_http):
    """
    Used to retrieve the username given a specific session token.
    """
    if token_http is None:
        return None
    token = Token.deserialize(token_http)
    return token.username


# Existence
def verify_device_existence(self, device_id: str) -> bool:
        device = mongo_adapter.retrieve_device(device_id)
        return bool(device)  # Restituisce True se il dispositivo esiste


def verify_greenhouse_existence(self, greenhouse_id: str) -> bool:
        greenhouse = mongo_adapter.retrieve_greenhouse(greenhouse_id)
        return bool(greenhouse)  # Restituisce True se la serra esiste


# Ownership
def retrieve_greenhouse_ownership(greenhouse_id):
    """
    Used to retrieve the owner of a specific greenhouse
    """
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    return greenhouses[greenhouse_id]['owner']


def retrieve_device_ownership(device_id):
    """
    Used to retrieve the owner of a specific device
    """
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    return devices[device_id]['owner']


def verify_greenhouse_ownership(greenhouse_id, username):
    """
    Used to verify if a greenhouse is owned by the user.
    """
    return retrieve_greenhouse_ownership(greenhouse_id) == username


def verify_device_ownership(device_id, username):
    """
    Used to verify if a device is owned by the user.
    """
    return retrieve_device_ownership(device_id) == username


def is_greenhouse_available(greenhouse_id):
    """
    Returns true if a greenhouse is available.
    """
    return retrieve_greenhouse_ownership(greenhouse_id) is None


def is_device_available(device_id):
    """
    Returns true if a device is available and ready to be associated to a greenhouse.
    """
    return retrieve_device_ownership(device_id) is None


# Retrieving
def retrieve_greenhouses(username):
    """
    Used to retrieve all the greenhouses owned by the given user.
    """
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    with open(DEVICES_LEGEND_FILE, 'r') as f:
        devices_legend = json.load(f)
    owned_greenhouses = users[username]['greenhouses']
    out_greenhouses = list()
    for greenhouse_id in owned_greenhouses:
        greenhouse = {
            'id': greenhouse_id,
            'name': greenhouses[greenhouse_id]['name'],
            'devices': []
        }
        gh_devices = retrieve_devices(greenhouse_id)
        for device_id in gh_devices:
            device_type = devices[device_id]["device_type"]
            device_name = devices[device_id]["name"]
            device = devices_legend[device_type]
            device['id'] = device_id
            device['name'] = device_name
            device['type'] = device_type
            greenhouse['devices'].append(device)
        out_greenhouses.append(greenhouse)
    return out_greenhouses


def retrieve_devices(greenhouse_id):
    """
    Used to retrieve all the devices registered under the given
    greenhouse.
    """
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    if greenhouse_id in greenhouses:
        return greenhouses[greenhouse_id]['devices']
    return None


# Association
def associate_greenhouse(greenhouse_id, greenhouse_name, username):
    """
    Used to associate a greenhouse to a user.
    """
    # Updating user's catalog
    with open(USERS_FILE, 'r') as f:
        users = json.load(f)
    users[username]['greenhouses'].append(greenhouse_id)
    with open(USERS_FILE, 'w') as f:
        f.write(json.dumps(users))
    # Updating greenhouses' catalog
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    greenhouses[greenhouse_id]['owner'] = username
    greenhouses[greenhouse_id]['name'] = greenhouse_name
    with open(GREENHOUSES_FILE, 'w') as f:
        f.write(json.dumps(greenhouses))


def associate_device(device_id, greenhouse_id, device_name, username):
    """
    Used to associate a device to a user and its greenhouse.
    """
    # Updating greenhouses' catalog
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    greenhouses[greenhouse_id]['devices'].append(device_id)
    with open(GREENHOUSES_FILE, 'w') as f:
        f.write(json.dumps(greenhouses))
    # Updating devices' catalog
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    devices[device_id]['owner'] = username
    devices[device_id]['associated_greenhouse'] = greenhouse_id
    devices[device_id]['name'] = device_name
    with open(DEVICES_FILE, 'w') as f:
        f.write(json.dumps(devices))


def retrieve_device_association(device_id):
    """
    Used to retrieve the greenhouse associated to the given device.
    Note: if device is not associated, it will return None.
    """
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    return devices[device_id]['associated_greenhouse']


# ------------------- DEVICE STATUS (anagrafica: legacy; runtime in services.json) -------------------

def retrieve_device_status(device_id: str):
    """
    Legacy: legge 'status' da devices.json se presente (evitare in produzione).
    Per il runtime vero usare services/services.json via resolver GET /device/status.
    """
    with open(DEVICES_FILE, 'r') as file:
        devices = json.load(file)
    if device_id not in devices:
        return None
    return devices[device_id].get('status', 'unknown')


def update_device_status(device_id: str, new_status: str):
    """
    Legacy: scrive 'status' in devices.json (solo per compatibilità).
    Il runtime corretto viene gestito dal resolver in services.json.
    """
    with open(DEVICES_FILE, 'r') as file:
        devices = json.load(file)
    if device_id not in devices:
        return False
    devices[device_id]['status'] = new_status
    with open(DEVICES_FILE, 'w') as file:
        json.dump(devices, file, indent=2)
    return True


# ------------------- CROPS (solo lettura preset) -------------------

def list_crops():
    with open(CROP_PROFILES_FILE, 'r') as f:
        return json.load(f)


# ------------------- STRATEGY & CROPS -------------------

def _available_roles_in_greenhouse(greenhouse_id):
    """
    Raccoglie i roles effettivi dei device associati alla serra
    filtrando devices.json per greenhouse_id.
    """
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    roles = set()
    for d in devices.values():
        if d.get('greenhouse_id') == greenhouse_id and d.get('role'):
            roles.add(d['role'])
    return roles


def set_crop_for_greenhouse(greenhouse_id: str, crop: str, username: str):
    if not verify_greenhouse_existence(greenhouse_id):
        return None, 'greenhouse_not_available'
    if not verify_greenhouse_ownership(greenhouse_id, username):
        return None, 'greenhouse_not_available'

    with open(CROP_PROFILES_FILE, 'r') as f:
        profiles = json.load(f)
    if crop not in profiles:
        return None, 'crop_not_found'
    profile = profiles[crop]

    roles_ok = _available_roles_in_greenhouse(greenhouse_id)

    cloned = {
        "crop": crop,
        "profile_version": profile.get("version", 1),
        "targets": profile.get("targets", {}),
        "controls": {}
    }
    for role, ctrl in profile.get("controls", {}).items():
        if role in roles_ok:
            cloned["controls"][role] = ctrl

    with open(STRATEGIES_FILE, 'r') as f:
        strategies = json.load(f)
    strategies[greenhouse_id] = cloned
    with open(STRATEGIES_FILE, 'w') as f:
        json.dump(strategies, f, indent=2)

    return cloned, None


def update_strategy(greenhouse_id: str, username: str, update: dict):
    if not verify_greenhouse_existence(greenhouse_id):
        return None, 'greenhouse_not_available'
    if not verify_greenhouse_ownership(greenhouse_id, username):
        return None, 'greenhouse_not_available'

    with open(STRATEGIES_FILE, 'r') as f:
        strategies = json.load(f)
    if greenhouse_id not in strategies:
        return None, 'strategy_not_found'

    current = strategies[greenhouse_id]

    if 'targets' in update and isinstance(update['targets'], dict):
        for k, v in update['targets'].items():
            if isinstance(v, dict):
                mn = v.get('min')
                mx = v.get('max')
                if mn is not None and mx is not None and mn >= mx:
                    return None, f'invalid_range_{k}'
                current.setdefault('targets', {})
                cur = current['targets'].get(k, {})
                cur.update(v)
                current['targets'][k] = cur

    if 'controls' in update and isinstance(update['controls'], dict):
        roles_ok = _available_roles_in_greenhouse(greenhouse_id)
        for role, ctrl_patch in update['controls'].items():
            if role not in roles_ok:
                return None, f'role_not_available:{role}'
            base = current['controls'].get(role, {})
            if not isinstance(ctrl_patch, dict):
                return None, f'invalid_control:{role}'
            base.update(ctrl_patch)
            current['controls'][role] = base

    strategies[greenhouse_id] = current
    with open(STRATEGIES_FILE, 'w') as f:
        json.dump(strategies, f, indent=2)
    return current, None

def retrieve_greenhouses_from_mongo(username: str):
    """
    Test: invece di leggere da greenhouses.json, chiediamo le serre
    al microservizio Mongo Adapter.
    username -> usato come 'tenant' per il filtro.
    """
    url = f"{MONGO_ADAPTER_URL}/greenhouses"
    try:
        resp = requests.get(url, params={"username": username}, timeout=5)
        resp.raise_for_status()
    except Exception as e:
        print("Errore chiamando Mongo Adapter:", e)
        return []

    data = resp.json()
    # Il resolver originale si aspetta una lista di ID serre
    return [gh.get("greenhouse_id") for gh in data.get("items", []) if gh.get("greenhouse_id")]


if __name__ == '__main__':
    pprint(retrieve_greenhouses('alice88'))
