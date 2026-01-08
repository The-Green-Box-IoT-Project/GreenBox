import os
from typing import Any, List
import requests
from requests.exceptions import RequestException


def get_all_stats_zones():
    base = os.environ.get("MONGO_ADAPTER_URL").rstrip("/")
    try:
        r = requests.get(f"{base}/statistics/zones", timeout=5)
        r.raise_for_status()
        return r.json()
    except RequestException as e:
        print(f"[WARNING] Errore recupero zone da {base}: {e}")
        return []

def get_measurements():
    base = os.environ.get("MONGO_ADAPTER_URL").rstrip("/")
    try:
        r = requests.get(f"{base}/statistics/measurements", timeout=5)
        r.raise_for_status()
        return r.json()
    except RequestException as e:
        print(f"[WARNING] Errore recupero metrics config da {base}: {e}")
        return []

def get_readings(
    metric,
    device,
    start,
    end,
) -> List[List[Any]]:

    # 1. Controllo di sicurezza: se la variabile d'ambiente manca, 
    # .rstrip() su None farebbe crashare il thread con AttributeError.
    base_env = os.environ.get("INFLUX_ADAPTER_URL")
    if not base_env:
        print("[ERROR] Variabile INFLUX_ADAPTER_URL non definita.")
        return []

    base_url = base_env.rstrip("/")
    url = f"{base_url}/measurements"

    params = {
        "measurement_type": metric,  
        "device_id": device,
        "start_time": start,
        "end_time": end
    }   

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json() 
    except requests.exceptions.RequestException as e:
        # 2. Log leggermente più dettagliato per capire quale servizio fallisce
        print(f"[WARNING] Errore lettura dati Influx ({url}): {e}")
        return []
