from typing import Optional, Any
from influxdb_client_3 import InfluxDBClient3
import pandas as pd
from dotenv import load_dotenv
import os

from greenbox.influx.queries import Queries


class InfluxDBAdapter:
    """
    Minimal wrapper around InfluxDBClient3 for managing connection and queries.
    """

    def __init__(
        self,
        timeout: int = 30,
    ) -> None:
        """
        Initialize the client but do not connect yet.
        Environment variables are used to configure the connection:
        - INFLUXDB_URL: InfluxDB server URL.
        - INFLUXDB_TOKEN: API token for authentication.
        - INFLUXDB_BUCKET: Default bucket to use for queries.
        - INFLUXDB_ORG: Organization name (optional, can be empty).
        :param timeout: Request timeout in seconds.
        """
        self._host = os.getenv("INFLUXDB_URL")
        self._token = os.getenv("INFLUXDB_TOKEN")
        self._database = os.getenv("INFLUXDB_BUCKET")
        self._org = os.getenv("INFLUXDB_ORG")
        self._timeout = timeout or 30

        self._client: Optional[InfluxDBClient3] = None

    def connect(self) -> None:
        """
        Create the underlying InfluxDBClient3 instance if not already created.
        """
        if self._client is not None:
            return

        self._client = InfluxDBClient3(
            host=self._host,
            token=self._token,
            org=self._org,
            database=self._database,
            timeout=self._timeout,
        )

    def close(self) -> None:
        """
        Close the underlying client and release resources.
        """
        if self._client is not None:
            self._client.close()
            self._client = None

    def _ensure_client(self) -> InfluxDBClient3:
        """
        Internal helper to guarantee that the client is connected.
        """
        if self._client is None:
            self.connect()
        # mypy/typing hint
        assert self._client is not None
        return self._client

    def query(self, sql: str, **kwargs: Any) -> Any:
        """
        Execute a raw SQL query and return the low-level query result.

        :param sql: SQL query string.
        :param kwargs: Extra keyword arguments passed to client.query().
        :return: InfluxDB query result object.
        """
        client = self._ensure_client()
        return client.query(sql, **kwargs)

    def query_dataframe(self, sql: str, **kwargs: Any) -> pd.DataFrame:
        """
        Execute a SQL query and return the result as a pandas DataFrame.

        :param sql: SQL query string.
        :param kwargs: Extra keyword arguments passed to client.query().
        :return: pandas.DataFrame with the query result.
        """
        result = self.query(sql, **kwargs)
        return result.to_pandas()

    # Optional: context manager support
    def __enter__(self) -> "InfluxDBAdapter":
        """
        Allow usage with 'with' statement:
            with InfluxDB3Client(...) as client: ...
        """
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """
        Close the client when exiting a 'with' block.
        """
        self.close()


if __name__ == "__main__":
    # Example usage
    load_dotenv()  # Load environment variables from .env file

    client = InfluxDBAdapter()

    sql = Queries.sensor_data(
        "temperature", time_range="last_hour", limit=10, order_desc=False
    )
    print(client.query_dataframe(sql))
