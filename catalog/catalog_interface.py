import json
import os
import requests
import uuid
from pathlib import Path
from .auth_token import Token

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'

# Load configuration
with open(CONFIG_FILE, 'r') as f:
    config = json.load(f)

MONGO_ADAPTER_URL = os.getenv("MONGO_ADAPTER_URL", config.get("mongo_adapter_url", "http://127.0.0.1:8082"))
INFLUX_ADAPTER_URL = os.getenv("INFLUX_ADAPTER_URL", config.get("influx_adapter_url", "http://127.0.0.1:8086"))
BROKER_IP = os.getenv("BROKER_IP", config.get("broker_ip", "127.0.0.1"))
BROKER_PORT = int(os.getenv("BROKER_PORT", config.get("broker_port", 1883)))

def retrieve_broker():
    return BROKER_IP, BROKER_PORT

# --- Auth ---
def signup_user(username, password, email):
    url = f"{MONGO_ADAPTER_URL}/users"
    try:
        response = requests.post(url, json={"username": username, "password": password, "email": email})
        return response.status_code == 200 or response.status_code == 201
    except requests.RequestException:
        return False

def validate_login(username, password):
    url = f"{MONGO_ADAPTER_URL}/login"
    try:
        response = requests.post(url, json={"username": username, "password": password})
        if response.status_code == 200:
            token = Token.generate(username)
            return Token.serialize(token)
        return None
    except requests.RequestException:
        return None

def verify_token(token_http):
    if token_http is None:
        return False
    return not Token.deserialize(token_http).is_expired()

def retrieve_username_by_token(token_http):
    if token_http is None:
        return None
    token = Token.deserialize(token_http)
    return token.username

# --- Greenhouses ---
def retrieve_greenhouses(username):
    url = f"{MONGO_ADAPTER_URL}/greenhouses"
    try:
        response = requests.get(url, params={"username": username})
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except requests.RequestException:
        return []

def add_greenhouse(name, username):
    url = f"{MONGO_ADAPTER_URL}/greenhouses"
    greenhouse_id = str(uuid.uuid4())
    try:
        response = requests.post(url, json={
            "greenhouse_id": greenhouse_id,
            "name": name, 
            "owner": username
        })
        return response.status_code == 200 or response.status_code == 201
    except requests.RequestException:
        return False

def retrieve_greenhouse(greenhouse_id):
    url = f"{MONGO_ADAPTER_URL}/greenhouses/{greenhouse_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def rename_greenhouse(greenhouse_id, name, username):
    url = f"{MONGO_ADAPTER_URL}/greenhouses/{greenhouse_id}"
    try:
        response = requests.put(url, params={"username": username}, json={"name": name})
        return response.status_code == 200
    except requests.RequestException:
        return False

def delete_greenhouse(greenhouse_id, username):
    url = f"{MONGO_ADAPTER_URL}/greenhouses/{greenhouse_id}"
    try:
        response = requests.delete(url, params={"username": username})
        return response.status_code == 200
    except requests.RequestException:
        return False

# --- Zones ---
def retrieve_zones(greenhouse_id):
    url = f"{MONGO_ADAPTER_URL}/zones"
    try:
        response = requests.get(url, params={"greenhouse_id": greenhouse_id})
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except requests.RequestException:
        return []

def retrieve_zone(zone_id):
    url = f"{MONGO_ADAPTER_URL}/zones/{zone_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

def add_zone(greenhouse_id, zone_id, zone_name, username):
    url = f"{MONGO_ADAPTER_URL}/zones"
    try:
        response = requests.put(
            url,
            params={"username": username},
            json={"greenhouse_id": greenhouse_id, "zone_id": zone_id, "name": zone_name},
        )
        return response.status_code == 200
    except requests.RequestException:
        return False

def rename_zone(zone_id, zone_name, username):
    url = f"{MONGO_ADAPTER_URL}/zones/{zone_id}"
    try:
        response = requests.put(url, params={"username": username}, json={"name": zone_name})
        return response.status_code == 200
    except requests.RequestException:
        return False

def delete_zone(zone_id, username):
    url = f"{MONGO_ADAPTER_URL}/zones/{zone_id}"
    try:
        response = requests.delete(url, params={"username": username})
        return response.status_code == 200
    except requests.RequestException:
        return False

def modify_control_strategy(zone_id, thresholds, username):
    url = f"{MONGO_ADAPTER_URL}/zones/{zone_id}/strategy"
    try:
        response = requests.put(url, params={"username": username}, json=thresholds)
        return response.status_code == 200
    except requests.RequestException:
        return False

def retrieve_control_strategy(zone_id):
    url = f"{MONGO_ADAPTER_URL}/zones/{zone_id}/strategy"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return {}
    except requests.RequestException:
        return {}

# --- Devices ---
def retrieve_devices(zone_id):
    url = f"{MONGO_ADAPTER_URL}/devices"
    try:
        response = requests.get(url, params={"zone_id": zone_id})
        if response.status_code == 200:
            return response.json().get("items", [])
        return []
    except requests.RequestException:
        return []

def retrieve_actuator_status(device_id):
    url = f"{MONGO_ADAPTER_URL}/devices/{device_id}/status"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get("status")
        return False
    except requests.RequestException:
        return False

def retrieve_device(device_id):
    url = f"{MONGO_ADAPTER_URL}/devices/{device_id}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.RequestException:
        return None

# --- Measurements (Influx) ---
def retrieve_measurements(device_id, measurement_type, start_time, end_time):
    url = f"{INFLUX_ADAPTER_URL}/measurements"
    params = {
        "device_id": device_id,
        "measurement_type": measurement_type,
        "start_time": start_time,
        "end_time": end_time
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []

def retrieve_last_measurements(device_id):
    url = f"{INFLUX_ADAPTER_URL}/measurements/last"
    params = {"device_id": device_id}
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return {}
    except requests.RequestException:
        return {}

def retrieve_actuator_consumption(device_id, start_time, end_time):
    url = f"{INFLUX_ADAPTER_URL}/consumption"
    params = {
        "device_id": device_id,
        "start_time": start_time,
        "end_time": end_time
    }
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            return response.json()
        return []
    except requests.RequestException:
        return []
