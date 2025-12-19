import os
import requests
import json
import pandas as pd
from typing import List, Dict, Any, Tuple, Set

from greenbox.sim.thresholds.thresholds import Threshold

# --- Low-Level API Functions ---


def catalog_url() -> str:
    """Return base URL from CATALOG_URL env var (no trailing slash)."""
    url = os.getenv("CATALOG_URL")
    if not url:
        raise ValueError("CATALOG_URL is required")
    return url.rstrip("/")


def login(username: str, password: str) -> str:
    """Authenticate and return user token. Handles multiple response formats."""
    r = requests.post(f"{catalog_url()}/login", json={"username": username, "password": password}, timeout=5)
    
    # If the login POST itself fails (e.g., 401, 403, 500), raise immediately.
    r.raise_for_status()

    # The server can be inconsistent. We need to try multiple ways to get the token.
    try:
        # Ideal case: the response is a JSON object like {"token": "value"}
        data = r.json()
        if isinstance(data, dict):
            token = data.get("token")
            if token:
                return str(token)
        
        # Case: the response is a JSON string like "\"the_token\""
        if isinstance(data, str):
            # It might be a double-encoded JSON, try to parse it again
            try:
                inner_data = json.loads(data)
                if isinstance(inner_data, dict) and "token" in inner_data:
                    return str(inner_data["token"])
                # If after parsing it's still a string, it must be the token
                return str(inner_data)
            except json.JSONDecodeError:
                 # It was just a plain string in the JSON, so it's the token
                return data

    except json.JSONDecodeError:
        # Case: the response is not JSON at all. The raw text must be the token.
        token = r.text.strip()
        # A simple but effective heuristic: tokens are usually single long strings without spaces.
        # Error messages usually have spaces.
        if ' ' in token or '<' in token: # Check for spaces or HTML tags
             raise ValueError(f"Authentication may have failed. Server returned a non-token response: {token}")
        if not token:
            raise ValueError("Authentication failed: received an empty non-JSON response.")
        return token
    
    raise ValueError(f"Could not extract a valid token from server response: {r.text}")


def get_broker_info() -> Tuple[str, int]:
    """Get MQTT broker ip/port from catalog."""
    r = requests.get(f"{catalog_url()}/broker", timeout=5)
    r.raise_for_status()
    j = r.json()
    return j["broker_ip"], j["broker_port"]


def get_greenhouses(token: str) -> List[Dict[str, Any]]:
    """Return the list of greenhouses (id + name) for the user."""
    r = requests.get(
        f"{catalog_url()}/greenhouses", headers={"token": token}, timeout=5
    )
    r.raise_for_status()
    data = r.json()
    if isinstance(data, list):
        return data
    raise ValueError("Unexpected payload when retrieving greenhouses")


def _get_zones(token: str, greenhouse_id: str) -> List[Dict[str, Any]]:
    """Return zones for the given greenhouse."""
    if not greenhouse_id:
        return []
    r = requests.get(
        f"{catalog_url()}/zones",
        headers={"token": token},
        params={"greenhouse_id": greenhouse_id},
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def _get_devices(token: str, zone_id: str) -> List[Dict[str, Any]]:
    """Return devices registered for the given zone."""
    if not zone_id:
        return []
    r = requests.get(
        f"{catalog_url()}/devices",
        headers={"token": token},
        params={"zone_id": zone_id},
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, list) else []


def _get_zone_strategy(token: str, zone_id: str) -> Dict[str, Any]:
    """Retrieve the normalized strategy for a zone."""
    if not zone_id:
        return {}
    r = requests.get(
        f"{catalog_url()}/zones/strategy",
        headers={"token": token},
        params={"zone_id": zone_id},
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    return data if isinstance(data, dict) else {}


# --- High-Level Service-Specific Functions ---


def get_device_config(device_id: str) -> Dict[str, Any]:
    """
    (Used by: raspberry)
    Retrieves the context configuration for a single device from the catalog.
    """
    username = os.getenv("USER")
    password = os.getenv("PASSWORD")
    if not (username and password):
        raise ValueError("USER and PASSWORD are required for authentication.")

    token = login(username, password)
    broker_ip, broker_port = get_broker_info()
    greenhouses_data = get_greenhouses(token)

    for gh in greenhouses_data:
        gh_id = gh.get("id")
        if not gh_id:
            continue

        zones = _get_zones(token, gh_id)
        for zone in zones:
            zone_id = zone.get("id")
            if not zone_id:
                continue
            devices = _get_devices(token, zone_id)
            for device in devices:
                if (
                    device.get("type") == "raspberry"
                    and device.get("id") == device_id
                ):
                    return {
                        "greenhouse_id": gh_id,
                        "broker_ip": broker_ip,
                        "broker_port": broker_port,
                    }

    raise ValueError(
        f"Device with ID '{device_id}' not found in any greenhouse for this user."
    )


def get_all_zones_with_measurements() -> Dict[str, Any]:
    """
    (Used by: statistics)
    Returns a dictionary containing broker info and a structured list of all zones
    with their associated measurements.
    """
    username = os.getenv("USER")
    password = os.getenv("PASSWORD")
    if not (username and password):
        raise ValueError("USER and PASSWORD are required for authentication.")

    token = login(username, password)
    broker_ip, broker_port = get_broker_info()
    greenhouses_data = get_greenhouses(token)

    processed_greenhouses = []
    for gh in greenhouses_data:
        gh_id = gh.get("id")
        if not gh_id:
            continue

        raspberry_ids: Set[str] = set()
        measurement_names: Set[str] = set()

        zones = _get_zones(token, gh_id)
        for zone in zones:
            zone_id = zone.get("id")
            if not zone_id:
                continue

            for device in _get_devices(token, zone_id):
                dev_id = device.get("id")
                if device.get("type") == "raspberry" and dev_id:
                    raspberry_ids.add(str(dev_id))

            strategy = _get_zone_strategy(token, zone_id)
            for metric in strategy.keys():
                if isinstance(metric, str) and metric:
                    measurement_names.add(metric)

        processed_greenhouses.append(
            {
                "greenhouse_id": gh_id,
                "raspberries": sorted(raspberry_ids),
                "measurements": sorted(measurement_names),
            }
        )

    return {
        "broker_ip": broker_ip,
        "broker_port": broker_port,
        "greenhouses": processed_greenhouses,
    }


def get_thresholds_config(greenhouse_id: str) -> Dict[str, Threshold]:
    """
    Retrieve threshold configuration directly from the catalog (Mongo backend).
    """
    if not greenhouse_id:
        raise ValueError("greenhouse_id is required for thresholds retrieval.")

    r = requests.get(
        f"{catalog_url()}/greenhouses/{greenhouse_id}/thresholds",
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    payload = data.get("thresholds") if isinstance(data, dict) else data

    if not isinstance(payload, dict) or not payload:
        raise RuntimeError(f"No thresholds configured for greenhouse {greenhouse_id}")

    normalized: Dict[str, Threshold] = {}
    for metric, cfg in payload.items():
        if not isinstance(cfg, dict):
            continue
        lower = cfg.get("min") or cfg.get("lower")
        upper = cfg.get("max") or cfg.get("upper")
        deadband = cfg.get("deadband") or cfg.get("dead_band") or cfg.get("tolerance") or 0.0
        if lower is None or upper is None:
            raise ValueError(f"Threshold missing bounds for metric '{metric}'")
        normalized[metric] = Threshold(float(lower), float(upper), float(deadband or 0.0))

    if not normalized:
        raise RuntimeError(f"Threshold payload empty for greenhouse {greenhouse_id}")
    return normalized


def get_effects_config(greenhouse_id: str) -> pd.DataFrame:
    """
    Retrieve actuator effects configuration directly from the catalog (Mongo backend).
    """
    if not greenhouse_id:
        raise ValueError("greenhouse_id is required for effects retrieval.")

    r = requests.get(
        f"{catalog_url()}/greenhouses/{greenhouse_id}/effects",
        timeout=5,
    )
    r.raise_for_status()
    data = r.json()
    payload = data.get("effects") if isinstance(data, dict) else data

    if not isinstance(payload, list) or not payload:
        raise RuntimeError(f"No actuator effects configured for greenhouse {greenhouse_id}")

    return pd.DataFrame(payload)
