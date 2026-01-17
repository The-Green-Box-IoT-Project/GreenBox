import cherrypy
import os
from math import ceil
from typing import Iterable, Optional
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
import pandas as pd

from adapter import InfluxDBAdapter
from queries import Queries

DEFAULT_TZ = ZoneInfo("Europe/Rome")


def _normalize_time_param(s: Optional[str]) -> Optional[str]:
    """
    Converte start_time/end_time in una stringa RFC3339 UTC.
    - Se s è naive (senza tz), assume Europe/Rome.
    - Se s ha Z o offset, lo rispetta.
    Ritorna stringa tipo: '2026-01-16T15:00:00Z'
    """
    if not s:
        return None

    # Supporta 'Z' (RFC3339) convertendolo in formato compatibile con fromisoformat
    dt = datetime.fromisoformat(s.replace("Z", "+00:00"))

    # Se manca timezone -> assumo Europe/Rome
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=DEFAULT_TZ)

    # Normalizzo a UTC
    dt_utc = dt.astimezone(timezone.utc)

    # Tolgo microsecondi per avere stringhe pulite e stabili
    dt_utc = dt_utc.replace(microsecond=0)

    # Ritorno con 'Z'
    return dt_utc.isoformat().replace("+00:00", "Z")


def _to_local_iso(s: str) -> str:
    # s arriva spesso come '2026-01-16 15:23:36+00:00' o simile
    dt = pd.to_datetime(s, utc=True, errors="coerce")
    if pd.isna(dt):
        return str(s)
    return dt.tz_convert("Europe/Rome").isoformat()


class InfluxService:
    exposed = True

    def __init__(self):
        self._adapter = InfluxDBAdapter()
        self._adapter.connect()

    def read(
        self,
        metric: str,
        *,
        start: Optional[str] = None,
        end: Optional[str] = None,
        device: Optional[str] = None,
        limit: Optional[int] = None,
        order_desc: bool = True,
    ) -> pd.DataFrame:

        sql = Queries.sensor_data(
            metric,
            start=start,
            end=end,
            device=device,
            limit=limit,
            order_desc=order_desc,
        )
        return self._adapter.query_dataframe(sql, language="sql")

    @staticmethod
    def _aggregate_dataframe(
        df: pd.DataFrame,
        *,
        value_columns: Iterable[str],
        limit: int = 60,
    ) -> pd.DataFrame:
        if df.empty:
            return df
        if len(df) <= limit:
            return df

        df = df.copy()
        df["time"] = pd.to_datetime(df["time"], errors="coerce")
        df = df.dropna(subset=["time"]).sort_values("time")
        if df.empty:
            return df

        group_size = ceil(len(df) / limit)
        df["_bucket"] = [i // group_size for i in range(len(df))]
        agg_map = {col: "mean" for col in value_columns}
        out = df.groupby("_bucket", as_index=False).agg({"time": "first", **agg_map})
        return out.drop(columns=["_bucket"])

    @cherrypy.tools.json_out()
    def GET(self, *path, **params):
        # Basic liveness endpoint
        if path and path[0] == "health":
            return {"status": "ok"}

        if not path:
            return {"status": "Influx Adapter Ready"}

        if path[0] == "measurements":
            if len(path) == 1:
                # /measurements
                device_id = params.get("device_id")
                metric = params.get("measurement_type")
                start = _normalize_time_param(params.get("start_time"))
                end = _normalize_time_param(params.get("end_time"))

                if not metric:
                    raise cherrypy.HTTPError(400, "Missing measurement_type")

                try:
                    df = self.read(
                        metric=metric,
                        device=device_id,
                        start=start,
                        end=end,
                    )
                except ValueError:
                    return []

                result = []
                df = self._aggregate_dataframe(df, value_columns=["value"])
                if not df.empty:
                    for _, row in df.iterrows():
                        result.append(
                            [_to_local_iso(str(row.get("time"))), row.get("value")]
                        )
                return result

            elif len(path) == 2 and path[1] == "last":
                # /measurements/last
                device_id = params.get("device_id")
                metrics = Queries.METRICS
                out = {}
                for m in metrics:
                    try:
                        df = self.read(metric=m, device=device_id, limit=1)
                        if not df.empty:
                            out[m] = df.iloc[0]["value"]
                    except ValueError:
                        pass
                return out

        if path[0] == "consumption":
            # / consumption
            device_id = params.get("device_id")

            start = _normalize_time_param(params.get("start_time"))
            end = _normalize_time_param(params.get("end_time"))

            # 1. Usa la nuova query dettagliata
            sql = Queries.actuator_detailed(device_id, start, end)
            df = self._adapter.query_dataframe(sql, language="sql")

            # 2. Converti il DataFrame in una lista di dizionari
            result = []
            if not df.empty:
                df = df.fillna(0)
                df = self._aggregate_dataframe(df, value_columns=["level"])
                for _, row in df.iterrows():
                    result.append(
                        [_to_local_iso(str(row.get("time"))), row.get("level")]
                    )
            return result

        if path[0] == "actuators" and len(path) == 2 and path[1] == "last":
            # /actuators/last
            device_id = params.get("device_id")
            if not device_id:
                raise cherrypy.HTTPError(400, "Missing device_id")

            sql = Queries.actuator_last_level(device_id)
            df = self._adapter.query_dataframe(sql, language="sql")
            if df.empty:
                return {}

            row = df.iloc[0]
            try:
                level = float(row.get("level", 0))
            except (TypeError, ValueError):
                level = row.get("level")

            return {
                "device_id": device_id,
                "level": level,
                "time": str(row.get("time")),
            }

        raise cherrypy.HTTPError(404)


if __name__ == "__main__":
    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
            "tools.response_headers.on": True,
            "tools.response_headers.headers": [
                ("Content-Type", "application/json"),
                # Helpful when Grafana / browsers call this service directly.
                ("Access-Control-Allow-Origin", "*"),
                ("Access-Control-Allow-Methods", "GET, OPTIONS"),
                ("Access-Control-Allow-Headers", "Content-Type, Authorization"),
            ],
        }
    }
    port = int(os.environ.get("PORT", 8081))
    host = os.environ.get("HOST", "0.0.0.0")
    cherrypy.config.update({"server.socket_host": host, "server.socket_port": port})
    cherrypy.quickstart(InfluxService(), "/", conf)
