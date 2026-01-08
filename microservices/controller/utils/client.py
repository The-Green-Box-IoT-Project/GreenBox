import os
import requests
from typing import Any, Dict, Optional

def get_thresholds(
    username,
    zone_id
) -> Dict[str, Dict[str, Any]]:
    # Recupera l'URL base dalle variabili d'ambiente
    base_url = os.environ.get("MONGO_ADAPTER_URL")
    if not base_url:
        raise ValueError("Variabile d'ambiente MONGO_ADAPTER_URL non definita.")
    
    url = f"{base_url.rstrip('/')}/users/{username}/strategy"
    params = {
        "id": zone_id
    }   

    try:
        response = requests.get(url, params=params, timeout=5)
        response.raise_for_status()
        return response.json() 
    except requests.exceptions.RequestException as e:
        # 2. Log leggermente più dettagliato per capire quale servizio fallisce
        print(f"[WARNING] Errore lettura dati Influx ({url}): {e}")
        return {}

def get_device_context(greenhouse_id: str, device_id: str) -> Optional[Dict[str, str]]:
    """
    Esegue una reverse-lookup per ottenere username e zone_id partendo dal device.
    Restituisce None se l'associazione non viene trovata (404).
    """
    # Recupera l'URL base dalle variabili d'ambiente
    base_url = os.environ.get("MONGO_ADAPTER_URL")
    if not base_url:
        raise ValueError("Variabile d'ambiente MONGO_ADAPTER_URL non definita.")

    # Abbiamo spostato l'endpoint sotto /strategies per coerenza semantica
    url = f"{base_url.rstrip('/')}/strategies/lookup"
    
    params = {
        "greenhouse_id": greenhouse_id,
        "device_id": device_id
    }

    try:
        response = requests.get(url, params=params, timeout=5)
        
        # Se otteniamo 404, significa semplicemente che l'associazione non esiste
        if response.status_code == 404:
            return None
            
        # Per altri errori (500, 403, ecc), solleviamo un'eccezione
        response.raise_for_status()
        
        # Restituisce il dizionario: {"username": "...", "zone_id": "..."}
        return response.json()

    except requests.exceptions.RequestException as e:
        print(f"[ERROR] Errore durante il lookup del device {device_id} su {url}: {e}")
        # In caso di errore di rete restituisce None per non bloccare il flusso
        return None