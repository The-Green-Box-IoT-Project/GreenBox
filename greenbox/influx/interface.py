import logging
from typing import Optional

import cherrypy
import pandas as pd

from greenbox.influx.adapter import InfluxDBAdapter
from greenbox.influx.queries import Queries
from greenbox.utils.logging import setup_logger


class InfluxInterface:
    """
    Minimal helpers to read sensor data in InfluxDB.
    """

    def __init__(self, adapter: Optional[InfluxDBAdapter] = None) -> None:
        self._adapter = adapter or InfluxDBAdapter()
        self._adapter.connect()

    def read(
        self,
        metric: str,
        *,
        time_range: Optional[str] = None,
        start: Optional[str] = None,
        end: Optional[str] = None,
        device: Optional[str] = None,
        site: Optional[str] = None,
        limit: int = 100,
        order_desc: bool = True,
    ) -> pd.DataFrame:
        if metric not in Queries.METRICS:
            raise ValueError("unsupported metric")
        # hard cap on limit to avoid huge scans
        limit = min(int(limit), 10_000)

        if time_range and time_range not in Queries.TIME_RANGES:
            raise ValueError("unsupported time_range")

        sql = Queries.sensor_data(
            metric,
            time_range=time_range,
            start=start,
            end=end,
            device=device,
            site=site,
            limit=limit,
            order_desc=order_desc,
        )
        return self._adapter.query_dataframe(sql, language="sql")

class InfluxAPI:
    """
    CherryPy endpoint: GET for queries (read-only).
    """

    exposed = True

    def __init__(self, iface: Optional[InfluxInterface] = None) -> None:
        self._iface = iface or InfluxInterface()

    @cherrypy.tools.json_out()
    def GET(self, **params):
        metric = params.get("metric")
        if not metric:
            raise cherrypy.HTTPError(400, "missing 'metric'")
        try:
            limit = int(params.get("limit", 100))
        except (TypeError, ValueError):
            raise cherrypy.HTTPError(400, "invalid 'limit'")
        order_desc = params.get("order_desc", "true").lower() != "false"

        try:
            df = self._iface.read(
                metric=metric,
                time_range=params.get("time_range"),
                start=params.get("start"),
                end=params.get("end"),
                device=params.get("device"),
                site=params.get("site"),
                limit=limit,
                order_desc=order_desc,
            )

            # FIX: Convertiamo i timestamp in stringhe per renderli serializzabili in JSON
            if not df.empty and "time" in df.columns:
                df["time"] = df["time"].astype(str)

            logging.info(
                "GET metric=%s site=%s device=%s limit=%s time_range=%s start=%s end=%s rows=%s",
                metric,
                params.get("site"),
                params.get("device"),
                limit,
                params.get("time_range"),
                params.get("start"),
                params.get("end"),
                len(df),
            )
            return df.to_dict(orient="records")

        except ValueError as e:
            logging.warning("Bad request: %s", e)
            raise cherrypy.HTTPError(400, str(e))
        except Exception as e:
            cherrypy.log(f"ERRORE SERVER GET: {e}", traceback=True)
            raise cherrypy.HTTPError(500, "Internal Error")

if __name__ == "__main__":
    from dotenv import load_dotenv

    # Carica le variabili d'ambiente (.env) per la connessione al DB
    load_dotenv()
    setup_logger("influx_interface")

    cherrypy.config.update({"server.socket_port": 8081})

    conf = {
        "/": {
            "request.dispatch": cherrypy.dispatch.MethodDispatcher(),
            "tools.sessions.on": True,
            "tools.response_headers.on": True,
            "tools.response_headers.headers": [("Content-Type", "application/json")],
        }
    }

    # Montiamo la nuova classe InfluxAPI
    cherrypy.tree.mount(InfluxAPI(), "/", conf)

    # Opzionale: per renderlo accessibile dalla rete locale
    # cherrypy.config.update({'server.socket_host': '0.0.0.0'})

    cherrypy.engine.start()
    cherrypy.engine.block()
