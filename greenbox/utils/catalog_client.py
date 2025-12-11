import os
import requests
import json
import csv
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Tuple

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
    """Return the full greenhouses topology payload for the user."""
    r = requests.get(
        f"{catalog_url()}/retrieve/greenhouses", headers={"token": token}, timeout=5
    )
    r.raise_for_status()
    return r.json()["greenhouses"]


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

        for device in gh.get("devices", []):
            if device.get("type") == "raspberry" and device.get("id") == device_id:
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

        raspberries = [d for d in gh.get("devices", []) if d.get("type") == "raspberry"]
        sensors = [d for d in gh.get("devices", []) if "sensor" in d.get("name", "")]

        measurements = set()
        for sensor in sensors:
            for measurement in sensor.get("measurements", []):
                m_type = measurement.get("type")
                if m_type:
                    measurements.add(m_type)

        processed_greenhouses.append(
            {
                "greenhouse_id": gh_id,
                "raspberries": [rb.get("id") for rb in raspberries if rb.get("id")],
                "measurements": sorted(list(measurements)),
            }
        )

    return {
        "broker_ip": broker_ip,
        "broker_port": broker_port,
        "greenhouses": processed_greenhouses,
    }


def get_thresholds_config(greenhouse_id: str) -> Dict[str, Threshold]:
    """
    (Used by: controller)
    Artifice: Loads threshold configuration from the local CSV file.
    In the future, this will query the MongoDB `crop_profiles` collection.
    """
    # This path is relative to the project root, assuming utils is in a package
    thresholds_path = Path(__file__).parent.parent / "sim/thresholds/thresholds.csv"

    out: Dict[str, Threshold] = {}
    try:
        with thresholds_path.open(newline="", encoding="utf-8") as f:
            for r in csv.DictReader(f):
                rec = {
                    k.strip().lower(): (v if v != "" else None) for k, v in r.items()
                }
                name_raw = (rec.get("metric") or "").strip()
                name = (
                    "pH"
                    if name_raw.lower().replace("-", "").replace("_", "") == "ph"
                    else name_raw
                )
                lo = rec.get("lower", rec.get("min"))
                hi = rec.get("upper", rec.get("max"))
                db = rec.get(
                    "deadband", rec.get("dead_band", rec.get("tolerance", 0.0))
                )
                if lo is None or hi is None:
                    raise ValueError(f"Threshold missing bounds for metric '{name}'")
                out[name] = Threshold(float(lo), float(hi), float(db or 0.0))
    except FileNotFoundError:
        raise RuntimeError(
            f"CRITICAL: Thresholds configuration file not found at {thresholds_path}"
        )
    return out


def get_effects_config(greenhouse_id: str) -> pd.DataFrame:
    """
    (Used by: controller)
    Artifice: Loads actuator effects configuration from the local CSV file.
    In the future, this will query the MongoDB `actuator_effects` collection.
    """
    # This path is relative to the project root, assuming utils is in a package
    effects_path = Path(__file__).parent.parent / "sim/effects/effects.csv"
    try:
        return pd.read_csv(effects_path)
    except FileNotFoundError:
        raise RuntimeError(
            f"CRITICAL: Effects configuration file not found at {effects_path}"
        )
