from typing import Optional, Any, Dict

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
            os.getenv("INFLUXDB_DATABASE")
            or os.getenv("INFLUXDB_BUCKET")
            or "greenbox"
        )
        self._token = os.getenv("INFLUXDB_TOKEN")
        self._org = os.getenv("INFLUXDB_ORG")
        self._timeout = timeout or 30

        self._client: Optional[InfluxDBClient3] = None

    def connect(self) -> None:
        """
        Create the underlying InfluxDBClient3 instance if not already created.
        """
        if self._client is not None:
            return

        kwargs: Dict[str, Any] = {
            "host": self._host,
            "database": self._database
        }

        # Token/org are optional for local Core started with --without-auth.
        if self._token:
            kwargs["token"] = self._token
        if self._org:
            kwargs["org"] = self._org

        self._client = InfluxDBClient3(**kwargs)

        try:
            # Attempt to create the database on connect.
            # If it already exists, this might raise an exception which we ignore.
            self._client.query(f'CREATE DATABASE "{self._database}"', language="sql")
        except Exception:
            pass

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
