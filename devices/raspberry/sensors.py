import os
from dotenv import load_dotenv
import json
import threading
import logging

from devices.utils.mqtt import MyMQTT
from devices.sim.mockseries.mockseries import SimulateRealTimeReading

load_dotenv()


class Sensor:
    def __init__(self, config_dict, broker_ip, broker_port, base_topic):

        # Load sensor attribute
        self.device_id = config_dict["id"]
        self.measurements = config_dict[
            "measurements"
        ]  # List of measurement keys OR dicts
        self.units = config_dict[
            "units"
        ]  # Dict of measurement units (key is measurement)
        self.time_interval = float(os.getenv("TIME_INTERVAL_SENSORS", "5"))

        self.mqtt = MyMQTT(
            clientID=self.device_id, broker=broker_ip, port=broker_port, notifier=None
        )
        self.base_topic = base_topic
        topic_parts = base_topic.strip("/").split("/")
        self.site_id = topic_parts[0] if len(topic_parts) > 0 else None
        self.raspberry_id = topic_parts[1] if len(topic_parts) > 1 else None

        self._stop_event = threading.Event()

    def _build_publisher_topic(self, measurement_key):
        return self.base_topic + self.device_id + "/" + measurement_key

    def _build_payload(self, metric, raw_value):
        try:
            value = round(float(raw_value), 3)
        except (TypeError, ValueError):
            return None

        return {
            "value": value,
            "unit": self.units.get(metric),
            "sensor": self.device_id,
            "metric": metric,
            "site": self.site_id,
            "device": self.raspberry_id,
        }

    def hardware_read(self):
        raise NotImplementedError

    def start(self):
        self.mqtt.start()

    def stop(self):
        try:
            self.mqtt.stop()
        except Exception:
            logging.exception("[%s] Stop error", self.device_id)
        finally:
            logging.info("[%s] Stopped.", self.device_id)

    def send_value(self, value):
        """
        If value is a dict, look up each measurement by its 'field' key.
        If value is scalar, replicate to all measurements.
        """
        if isinstance(value, dict):
            for m in self.measurements:
                field = m.get("field") if isinstance(m, dict) else str(m)
                if field in value:
                    topic = self._build_publisher_topic(field)
                    payload = self._build_payload(field, value[field])
                    if payload is not None:
                        self.mqtt.MyPublish(topic, payload)
        else:
            for m in self.measurements:
                field = m.get("field") if isinstance(m, dict) else str(m)
                topic = self._build_publisher_topic(field)
                payload = self._build_payload(field, value)
                if payload is not None:
                    self.mqtt.MyPublish(topic, payload)

    def request_stop(self):
        """Signal the reading loop to stop gracefully."""
        self._stop_event.set()

    def loop(self, value_provider):
        """Periodically compute/read a value and publish."""
        self.start()
        try:
            while not self._stop_event.is_set():
                try:
                    value = value_provider()
                except Exception:
                    logging.exception("[%s] value_provider crashed", self.device_id)
                    break
                self.send_value(value)
                if self._stop_event.wait(timeout=self.time_interval):
                    break
        finally:
            self.stop()

    def read_value(self):
        # hardware_read must return {'temperature': ..., 'humidity': ...}
        self.loop(lambda: self.hardware_read())


class SensorSim(Sensor):
    """
    Simulated sensor: listens to actuator topics and applies per-field deltas
    before publishing the read value.
    """

    def __init__(self, config_dict, broker_ip, broker_port, base_topic):
        super().__init__(config_dict, broker_ip, broker_port, base_topic)
        # Stato per dinamica cumulativa: per ogni field memorizziamo base precedente (x) e valore pubblicato precedente (z)
        self._x_prev = {}
        self._z_prev = {}

        # Replace MQTT client with one that calls back here
        self.mqtt = MyMQTT(
            clientID=self.device_id, broker=broker_ip, port=broker_port, notifier=self
        )

        # Latest deltas per actuator, e.g. {"fan_001": {"temperature": -0.12, "humidity": -0.4}, ...}
        self._actuator_deltas = {}
        self._lock = threading.Lock()

        # Subscribe to all actuators' data for THIS specific zone (greenhouse/raspberry)
        self._actuator_topic = f"/{self.site_id}/{self.raspberry_id}/actuators/+/+/data"

    def notify(self, topic, payload):
        """
        Called by MyMQTT when a message arrives at subscribed actuator topics.
        Store the *latest* delta_<field> per actuator.
        Topic format: /<gh>/<rb>/actuators/<system>/<id>/data
        """
        try:
            payload_str = (
                payload.decode("utf-8", errors="ignore")
                if isinstance(payload, (bytes, bytearray))
                else str(payload)
            )
            data = json.loads(payload_str)
            if not isinstance(data, dict):
                return
        except Exception:
            return

        # Extract actuator_id from topic
        parts = topic.strip("/").split("/")
        try:
            i = parts.index("actuators")
            actuator_id = parts[i + 2]  # <system>=i+1, <id>=i+2
        except Exception:
            return

        with self._lock:
            slot = self._actuator_deltas.setdefault(actuator_id, {})
            for k, v in data.items():
                if isinstance(k, str) and k.startswith("delta_"):
                    field = k[len("delta_") :]
                    try:
                        slot[field] = float(v)  # overwrite: keep *latest* per actuator
                    except (TypeError, ValueError):
                        pass

    def start(self):
        super().start()
        # Listen to all actuators on this box
        self.mqtt.MySubscribe(self._actuator_topic)

    def stop(self):
        try:
            self.mqtt.MyUnsubscribe()
        except Exception as e:
            logging.debug("[%s] Unsubscribe skipped: %s", self.device_id, e)
        super().stop()

    def _apply_and_clear_deltas(self, value):
        """
        Applica i delta degli attuatori al valore generato dal simulatore.

        - Per metriche cumulative (es. temperature, humidity, soil_humidity, pH):
              z_i = z_{i-1} + (x_i - x_{i-1}) + u_i
          dove x_i e' il valore "naturale" generato dal mock (value), u_i e' la somma dei delta correnti.

        - Per la luce (istantanea):
              z = x + u
        """
        eps = 1e-12

        # Compute per-field totals and contributors (actuator ids)
        with self._lock:
            totals = {}
            contrib_ids = {}  # e.g. {"temperature": ["fan_001", "humid_003"], ...}
            for act_id, fields in self._actuator_deltas.items():
                for field, dv in fields.items():
                    try:
                        dv = float(dv)
                    except (TypeError, ValueError):
                        continue
                    if abs(dv) < eps:
                        continue
                    totals[field] = totals.get(field, 0.0) + dv
                    contrib_ids.setdefault(field, []).append(act_id)

        def _clamp_field(field: str, x: float) -> float:
            # Sensori pubblicano in %: clamp per evitare valori non fisici
            if field in ("humidity", "soil_humidity"):
                if x < 0.0:
                    return 0.0
                if x > 100.0:
                    return 100.0
            return x

        def _apply_one(field: str, base_x: float, delta_sum: float) -> float:
            # Luce: istantanea, non cumulativa
            if field == "light":
                return _clamp_field(field, base_x + delta_sum)

            # Prima osservazione: inizializziamo lo stato (se attuatori ON, ha senso partire gia' con x + delta)
            if field not in self._x_prev or field not in self._z_prev:
                z = _clamp_field(field, base_x + delta_sum)
                self._x_prev[field] = base_x
                self._z_prev[field] = z
                return z

            x_prev = float(self._x_prev[field])
            z_prev = float(self._z_prev[field])

            z = z_prev + (base_x - x_prev) + delta_sum
            z = _clamp_field(field, z)

            self._x_prev[field] = base_x
            self._z_prev[field] = z
            return z

        # Dict case
        if isinstance(value, dict):
            out = dict(value)
            applied = {}

            for m in self.measurements:
                field = m.get("field") if isinstance(m, dict) else str(m)
                if field not in out:
                    continue

                try:
                    base = float(out[field])
                except (TypeError, ValueError):
                    continue

                delta_sum = float(totals.get(field, 0.0))
                new_val = _apply_one(field, base, delta_sum)
                out[field] = new_val

                # Log solo se c'e' delta (o se vuoi estenderlo anche ai casi senza delta)
                if abs(delta_sum) > eps:
                    ids = sorted(set(contrib_ids.get(field, [])))
                    applied[field] = {
                        "base": round(base, 4),
                        "new": round(new_val, 4),
                        "delta_sum": round(delta_sum, 4),
                        "contributors": len(ids),
                        "actuators": ids,
                    }

            if applied:
                logging.info(
                    "[%s] Applied STATEFUL latest-per-actuator deltas: %s",
                    self.device_id,
                    applied,
                )
            return out

        # Scalar case (single measurement)
        if len(self.measurements) == 1:
            m = self.measurements[0]
            field = m.get("field") if isinstance(m, dict) else str(m)

            try:
                base = float(value)
            except (TypeError, ValueError):
                return value

            delta_sum = float(totals.get(field, 0.0))
            new_val = _apply_one(field, base, delta_sum)

            if abs(delta_sum) > eps:
                ids = sorted(set(contrib_ids.get(field, [])))
                logging.info(
                    "[%s] Applied STATEFUL delta on %s: base=%.4f, new=%.4f, "
                    "delta_sum=%.4f, contributors=%d, actuators=%s",
                    self.device_id,
                    field,
                    base,
                    new_val,
                    delta_sum,
                    len(ids),
                    ids,
                )
            return new_val

        return value

    # Override to inject the deltas just-in-time
    def send_value(self, value):
        adjusted = self._apply_and_clear_deltas(value)
        super().send_value(adjusted)

    def read_value(self):
        self.loop(self._fake_read)

    def _fake_read(self):
        # Support measurements as either strings or dicts with {"field": "..."}
        fields = [
            (m.get("field") if isinstance(m, dict) else str(m))
            for m in self.measurements
        ]

        if len(fields) == 1:
            return SimulateRealTimeReading(fields[0]).read()

        sensors = [f for f in fields if f != "light_natural"]
        readings = {f: SimulateRealTimeReading(f).read() for f in sensors}
        return readings
