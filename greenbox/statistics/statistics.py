import json
import logging
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import Iterable, Tuple

from greenbox.utils.catalog_client import log_to_catalog
from greenbox.utils.mqtt import MyMQTT


class _StatsBase:
    """Common wiring for Statistics and StatisticsSim."""
    WINDOW_MINUTES = 1  # hardcoded, used by both classes

    def __init__(self, measurement_name: str):

        # Measurement
        self.measurement_name = measurement_name

        # GET from catalog
        cfg = log_to_catalog()
        self.broker_ip = cfg["broker_ip"]
        self.broker_port = cfg["broker_port"]
        self.greenhouse_id = cfg["greenhouse_id"]
        self.raspberry_id = cfg["raspberry_id"]
        self.measurements = cfg["measurements"]

        # topics
        self.topic_publish = f"/{self.greenhouse_id}/{self.raspberry_id}/statistics/{self.measurement_name}"
        # sensors publish to: /{gh}/{rb}/sensors/<device_uuid>/<field>
        self.topic_subscribe = f"/{self.greenhouse_id}/{self.raspberry_id}/sensors/+/{self.measurement_name}"

        # mqtt
        self.client_id = f"stats_{self.measurement_name}"
        self.mqtt = MyMQTT(clientID=self.client_id,
                           broker=self.broker_ip,
                           port=self.broker_port,
                           notifier=self)

    def start(self):
        self.mqtt.start()
        self.mqtt.MySubscribe(self.topic_subscribe)

    def stop(self):
        try:
            self.mqtt.stop()
        except Exception:
            logging.exception("[%s] Stop error", self.client_id)
        finally:
            logging.info("[%s] Stopped.", self.client_id)


class Statistics(_StatsBase):
    """
    Normal statistics: compute from DB (InfluxDBSimulator) over WINDOW_MINUTES.
    Triggered by incoming sensor messages.
    """

    def __init__(self, measurement_name: str):
        super().__init__(measurement_name)
        from greenbox.utils.tools import convert_list_to_df
        from greenbox.influx.db_simulator import InfluxDBSimulator
        self._convert_list_to_df = convert_list_to_df
        self.window_minutes = int(self.WINDOW_MINUTES)
        self.ts_generator = InfluxDBSimulator(self.measurement_name)

    def _calculate_from_db(self):
        lst = self.ts_generator.query_last_minutes(self.window_minutes)
        df = self._convert_list_to_df(lst)
        if df.empty or self.measurement_name not in df:
            logging.debug("[%s] DB window has no data (last %d min).", self.client_id, self.window_minutes)
            return None
        s = df[self.measurement_name]
        stats = {
            "window": self.window_minutes,
            "max": round(float(s.max()), 3),
            "min": round(float(s.min()), 3),
            "median": round(float(s.median()), 3),
            "mean": round(float(s.mean()), 3),
            "std_dev": round(float(s.std()), 3),
        }
        logging.debug("[%s] DB stats computed: %s", self.client_id, stats)
        return stats

    # MQTT notifier
    def notify(self, topic, payload):
        try:
            stats = self._calculate_from_db()
            if stats is None:
                logging.debug("[%s] Nothing to publish (no data).", self.client_id)
                return
            self.mqtt.MyPublish(self.topic_publish, stats)
        except Exception:
            logging.exception("[%s] Notify error", self.client_id)


class StatisticsSim(_StatsBase):
    """
    Simulated statistics: keep a sliding buffer of WINDOW_MINUTES and compute
    stats on every new sensor value (once the buffer covers the whole window).
    """
    def __init__(self, measurement_name: str):
        super().__init__(measurement_name)
        self.window_minutes = int(self.WINDOW_MINUTES)
        self.window_td = timedelta(minutes=self.window_minutes)
        self._buf = deque()  # (ts, value)

    @staticmethod
    def _normalize_ts(ts: datetime) -> datetime:
        """Ensure timezone-aware (UTC) timestamps to avoid naive/aware issues."""
        if ts.tzinfo is None:
            return ts.replace(tzinfo=timezone.utc)
        return ts.astimezone(timezone.utc)

    @staticmethod
    def _calc(values):
        n = len(values)
        if n == 0:
            return None
        vals_sorted = sorted(values)
        mean = sum(values) / n
        median = vals_sorted[n // 2] if n % 2 else 0.5 * (vals_sorted[n // 2 - 1] + vals_sorted[n // 2])
        std = ((sum((x - mean) ** 2 for x in values) / (n - 1)) ** 0.5) if n > 1 else 0.0
        return {
            "max": round(max(values), 3),
            "min": round(min(values), 3),
            "median": round(median, 3),
            "mean": round(mean, 3),
            "std_dev": round(std, 3),
        }

    # MQTT notifier
    def notify(self, topic, payload):
        try:
            obj = json.loads(payload.decode("utf-8", errors="ignore"))
            if not isinstance(obj, dict) or "value" not in obj:
                logging.debug("[%s] Ignored message (no 'value'): %s", self.client_id, obj)
                return

            # parse ts (sensor payload is ISO8601 with offset or Z). fallback to now UTC.
            ts_str = obj.get("timestamp")
            try:
                ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00")) if ts_str else datetime.now(timezone.utc)
            except Exception:
                ts = datetime.now(timezone.utc)
            ts = self._normalize_ts(ts)

            try:
                val = float(obj["value"])
            except (TypeError, ValueError):
                logging.debug("[%s] Ignored message (value not float): %s", self.client_id, obj.get("value"))
                return

            # push
            self._buf.append((ts, val))

            buf_len = len(self._buf)
            span_sec = 0.0 if buf_len < 2 else (self._buf[-1][0] - self._buf[0][0]).total_seconds()

            # start publishing only when buffer spans the full window
            if not self._buf:
                return
            if span_sec < self.window_td.total_seconds():
                return

            values = [v for _, v in self._buf]
            payload_out = self._calc(values)
            if payload_out is None:
                return
            payload_out["window"] = self.window_minutes

            self.mqtt.MyPublish(self.topic_publish, payload_out)

        except Exception:
            logging.exception("[%s] Notify error", self.client_id)


class StatisticsHub:
    """
    Minimal lifecycle coordinator.
    Builds N workers (one per measurement) using the Statistics/StatisticsSim class-object.
    """

    def __init__(self, sim: bool, measurements: Iterable[str] = None):
        if measurements is None:
            measurements = log_to_catalog()["measurements"]
        self.workers = tuple(self._build_workers(sim, tuple(measurements)))

    @staticmethod
    def _build_workers(sim: bool, measurements: Tuple[str, ...]):
        if sim:
            return tuple(StatisticsSim(m) for m in measurements)
        else:
            return tuple(Statistics(m) for m in measurements)

    def start(self):
        for w in self.workers:
            w.start()

    def stop(self):
        for w in self.workers:
            try:
                w.stop()
            except Exception:
                pass
