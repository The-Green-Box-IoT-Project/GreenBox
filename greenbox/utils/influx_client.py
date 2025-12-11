import os
from typing import Optional, List, Dict, Any

import requests
from dotenv import load_dotenv


class InfluxInterfaceClient:
    """
    Client HTTP per interagire con il server Influx Interface.
    """

    def __init__(self, base_url: Optional[str] = None, timeout: float = 5.0):
        if base_url is None:
            base_url = os.getenv("INFLUX_INTERFACE_URL")
        self.base_url = base_url
        self.timeout = timeout

    def get_data(
        self,
        metric: str,
        limit: int = 100,
        order_desc: bool = True,
        time_range: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        device: Optional[str] = None,
        site: Optional[str] = None,
    ) -> List[Dict[str, Any]]:
        """
        Richiede dati al server (GET).
        """
        params = {
            "metric": metric,
            "limit": limit,
            "order_desc": str(order_desc).lower(),  # 'true' o 'false'
        }

        if time_range:
            params["time_range"] = time_range
        if start:
            params["start"] = start
        if end:
            params["end"] = end
        if device:
            params["device"] = device
        if site:
            params["site"] = site

        try:
            response = requests.get(self.base_url, params=params, timeout=self.timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Errore durante la lettura: {e}")
            return []


if __name__ == "__main__":
    load_dotenv()

    url = os.getenv("INFLUX_INTERFACE_URL")
    client = InfluxInterfaceClient(base_url=url)

    data = client.get_data(
        metric="temperature", limit=5, order_desc=True, time_range="last_hour"
    )

    if data:
        print(f"Trovati {len(data)} record per 'temperature':")
        for record in data:
            print(record)
    else:
        print("Nessun dato trovato.")
