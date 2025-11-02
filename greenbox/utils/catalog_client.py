import os
import requests
import json
from pprint import pprint


def catalog_url():
    """Return base URL from CATALOG_URL env var (no trailing slash)."""
    url = os.getenv("CATALOG_URL")
    if not url:
        raise ValueError("CATALOG_URL is required")
    return url.rstrip("/")


def login(username: str, password: str) -> str:
    """Authenticate and return user token."""
    r = requests.post(f"{catalog_url()}/login", json={"username": username, "password": password}, timeout=5)
    r.raise_for_status()
    data = r.json()
    if isinstance(data, str):
        data = json.loads(data)  # doppio parsing se necessario
    return data["token"]


def broker():
    """Get MQTT broker ip/port from catalog."""
    r = requests.get(f"{catalog_url()}/broker", timeout=5)
    r.raise_for_status()
    j = r.json()
    return j["broker_ip"], j["broker_port"]


def get_greenhouses(token: str):
    """Return the greenhouses payload for the user."""
    r = requests.get(f"{catalog_url()}/retrieve/greenhouses", headers={"token": token}, timeout=5)
    r.raise_for_status()
    return r.json()["greenhouses"]


def get_devices(greenhouses: list, gh_id: str):
    """Return the devices payload for the user."""
    raspberries = []
    actuators = []
    sensors = []
    for greenhouse in greenhouses:
        if greenhouse["id"] == gh_id:
            for device in greenhouse["devices"]:
                if device["type"] == "raspberry":
                    raspberries.append(device)
                elif "sensor" in device["name"]:
                    sensors.append(device)
                elif "actuator" in device["name"]:
                    actuators.append(device)
    return raspberries, actuators, sensors


def get_measurements(sensors: list):
    measurements = []
    for sensor in sensors:
        for measurement in sensor["measurements"]:
            measurements.append(measurement["type"])
    return measurements


def log_to_catalog():
    """
    Retrive every greenbox information from the catalog.
    """
    username = os.getenv("USER")
    password = os.getenv("PASSWORD")
    if not (username and password):
        raise ValueError("USER and PASSWORD are required")

    # 1. fai il login e ottieni il token
    token = login(username, password)  # base URL is taken inside login

    # 2. server riconosce user dal token e assegna il broker
    broker_ip, broker_port = broker()

    # 3. stessa cosa, ritorna le greenhouses associate al bro
    greenhouses = get_greenhouses(token)

    # 4. per semplicità facciamo che ha solo una serra
    gh_id = (greenhouses[0]["id"] if greenhouses else None)  # todo: una sola greenhouse per user!
    if not gh_id:
        raise RuntimeError("No greenhouse available for this user")

    # 5. Estraiamo ogni device associato alla greenbox
    raspberries, actuators, sensors = get_devices(greenhouses, gh_id)
    measurements = get_measurements(sensors)

    raspberry_id = (raspberries[0]["id"] if greenhouses else None)  # todo: una sola raspberry!
    if not raspberry_id:
        raise RuntimeError("No raspberry_id found; set RASPBERRY_ID or associate devices to a raspberry")

    return {
        "broker_ip": broker_ip,
        "broker_port": broker_port,
        "greenhouse_id": gh_id,
        "raspberry_id": raspberry_id,
        "actuators": actuators,
        "sensors": sensors,
        "measurements": measurements,
    }
