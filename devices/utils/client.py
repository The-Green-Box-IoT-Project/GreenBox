import requests
import os
import pandas as pd


def get_greenhouse_id(base_url, username, device_id):
    """
    Cerca in tutte le serre dell'utente per trovare in quale si trova il device.
    Restituisce l'ID della serra (es. 'GH_002') o None se non trovato.
    """
    # 1. Scarichiamo la lista delle serre dell'utente
    # Endpoint: GET /users/{username}/greenhouses
    resp = requests.get(f"{base_url}/users/{username}/greenhouses")
    if resp.status_code != 200:
        return None
    
    greenhouses = resp.json() # es: ["GH_001", "GH_002"]

    # 2. Entriamo in ogni serra per controllare le zone
    for gh_id in greenhouses:
        # Endpoint: GET /users/{username}/greenhouses?id=...
        gh_data = requests.get(f"{base_url}/users/{username}/greenhouses", params={"id": gh_id}).json()
        zones = gh_data.get("zones", [])

        # 3. Controlliamo ogni zona della serra
        for zone_id in zones:
            # Endpoint: GET /users/{username}/zones?id=...
            # L'adapter restituisce la lista degli ID dei device nel campo 'devices'
            z_data = requests.get(f"{base_url}/users/{username}/zones", params={"id": zone_id}).json()
            device_list = z_data.get("devices", [])

            if device_id in device_list:
                return gh_id  # Trovato!

    return None


def get_effects_config() -> pd.DataFrame:
    # 1. Calcolo del percorso del file (dinamico)
    base_dir = os.path.dirname(os.path.abspath(__file__))
    csv_file = os.path.join(base_dir, '..', 'sim', 'effects', 'effects.csv')
    csv_file = os.path.normpath(csv_file)

    if not os.path.exists(csv_file):
        raise FileNotFoundError(f"Impossibile trovare il file: {csv_file}")

    # 2. Lettura del CSV
    df = pd.read_csv(csv_file)

    # 3. FIX: NON tocchiamo la colonna 'level'.
    # Il tuo actuators.py cerca chiavi come "100%" o "25%".
    # Se la convertiamo in 1.0, la ricerca fallisce.

    # 4. Pulizia e Conversione delle colonne numeriche (Es. energy_consumption)
    # Selezioniamo tutte le colonne tranne quelle di testo
    cols_to_convert = [c for c in df.columns if c not in ['system', 'level']]
    
    for col in cols_to_convert:
        # 'errors="coerce"' trasforma eventuali valori sporchi (testo) in NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')

    # 5. Riempiamo i valori mancanti (NaN) con 0.0
    df[cols_to_convert] = df[cols_to_convert].fillna(0.0)

    return df
