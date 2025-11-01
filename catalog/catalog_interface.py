import json
from os import path
from pathlib import Path
from pprint import pprint

from catalog.token import Token

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
USERS_FILE = P / 'users.json'
SERVICES_FILE = P / 'services.json'
GREENHOUSES_FILE = P / 'generator' / 'greenhouses.json'
DEVICES_FILE = P / 'generator' / 'devices.json'
DEVICES_LEGEND_FILE = P / 'devices_legend.json'


def init():
    catalogs = [USERS_FILE, SERVICES_FILE]
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
def verify_greenhouse_existence(greenhouse_id):
    """
    Used to verify that a specified greenhouse is registered. This is
    to prevent that a user can claim a greenhouse that is not registered.
    """
    with open(GREENHOUSES_FILE, 'r') as f:
        greenhouses = json.load(f)
    if greenhouse_id in greenhouses:
        return True
    return False


def verify_device_existence(device_id):
    """
    Used to verify that a specified device is registered. This is
    to prevent that a user can associate a device that is not registered.
    """
    with open(DEVICES_FILE, 'r') as f:
        devices = json.load(f)
    if device_id in devices:
        return True
    return False


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


if __name__ == '__main__':
    pprint(retrieve_greenhouses('senpai'))
