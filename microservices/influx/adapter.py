from typing import Optional, Any, Dict
import json
import time
from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError

from influxdb_client_3 import InfluxDBClient3
import pandas as pd
import os


class InfluxDBAdapter:
    """
    Minimal wrapper around InfluxDBClient3 for managing connection and queries.
    """

    def __init__(self, timeout: int = 30) -> None:
        """
        Environment variables used:
        - INFLUXDB_URL: InfluxDB server URL
        - INFLUXDB_DATABASE: Database name (preferred)
        - INFLUXDB_BUCKET: Database name (legacy/back-compat)
        - INFLUXDB_TOKEN: Optional token (not needed when running InfluxDB3 Core with --without-auth)
        - INFLUXDB_ORG: Optional org (primarily for Cloud / Dedicated)
        """
        raw_host = os.getenv("INFLUXDB_URL")
        self._host = raw_host.rstrip("/")

        self._database = (
            os.getenv("INFLUXDB_DATABASE") or os.getenv("INFLUXDB_BUCKET") or "greenbox"
        )
        self._token = os.getenv("INFLUXDB_TOKEN")
        self._org = os.getenv("INFLUXDB_ORG")
        self._timeout = timeout or 30

        self._client: Optional[InfluxDBClient3] = None

    def _create_db_if_missing(self) -> None:
        """
        Crea il database su InfluxDB 3 Core tramite endpoint di configurazione.
        Idempotente: se esiste già, non rompe il flusso.
        """
        url = f"{self._host}/api/v3/configure/database"
        payload = json.dumps({"db": self._database}).encode("utf-8")

        req = Request(
            url=url,
            data=payload,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        # piccolo retry perché docker-compose "depends_on" NON aspetta readiness
        deadline = time.time() + 30  # 30s di tentativi
        last_err = None

        while time.time() < deadline:
            try:
                with urlopen(req, timeout=self._timeout) as resp:
                    # 201 Created oppure 204/200 a seconda delle versioni
                    if resp.status in (200, 201, 204):
                        return
            except HTTPError as e:
                # se "already exists" o simile, consideriamolo OK
                if e.code in (409,):
                    return
                last_err = e
            except URLError as e:
                last_err = e

            time.sleep(1)

        # se arrivi qui, non sei riuscito a creare/contattare Influx
        raise RuntimeError(
            f"Impossibile creare/verificare il DB '{self._database}': {last_err}"
        )

    def connect(self) -> None:
        if self._client is not None:
            return

        # 1) crea/assicura DB
        self._create_db_if_missing()

        # 2) ora puoi creare il client "con database"
        kwargs: Dict[str, Any] = {"host": self._host, "database": self._database}
        if self._token:
            kwargs["token"] = self._token
        if self._org:
            kwargs["org"] = self._org

        self._client = InfluxDBClient3(**kwargs)

    def close(self) -> None:
        if self._client is not None:
            self._client.close()
            self._client = None

    def _ensure_client(self) -> InfluxDBClient3:
        if self._client is None:
            self.connect()
        assert self._client is not None
        return self._client

    def query(self, sql: str, **kwargs: Any) -> Any:
        client = self._ensure_client()
        # Default to SQL unless the caller overrides.
        kwargs.setdefault("language", "sql")
        return client.query(sql, **kwargs)

    def query_dataframe(self, sql: str, **kwargs: Any) -> pd.DataFrame:
        result = self.query(sql, **kwargs)
        return result.to_pandas()

    def __enter__(self) -> "InfluxDBAdapter":
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
