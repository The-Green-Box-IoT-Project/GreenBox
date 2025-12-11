import os
from dotenv import load_dotenv
import json
import threading
import logging

from greenbox.utils.mqtt import MyMQTT
from greenbox.sim.mockseries.mockseries import SimulateRealTimeReading

load_dotenv()


class Sensor:
    def __init__(self, config_dict, broker_ip, broker_port, base_topic):

        # Load sensor attribute
        self.device_id = config_dict["id"]
        self.measurements = config_dict["measurements"]  # List of measurement keys
        self.units = config_dict[
            "units"
        ]  # Dict of measurement units (key is measurement)
        self.time_interval = float(os.getenv("TIME_INTERVAL_SENSORS"))
        # self.time_interval = os.getenv("TIME_INTERVAL_SENSORS")

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
        # Replace MQTT client with one that calls back here
        self.mqtt = MyMQTT(
            clientID=self.device_id, broker=broker_ip, port=broker_port, notifier=self
        )

        # Latest deltas per actuator, e.g. {"fan_001": {"temperature": -0.12, "humidity": -0.4}, ...}
        self._actuator_deltas = {}
        self._lock = threading.Lock()

        # Subscribe to all actuators' data for THIS specific zone (greenhouse/raspberry)
        self._actuator_topic = f"/{self.site_id}/{self.raspberry_id}/actuators/+/+/data"
        # self._actuator_topic = (
        #     self.base_topic.replace(f"/+/sensors/", "/actuators/") + "+/+/data"
        # )

    def notify(self, topic, payload):
        """
        Called by MyMQTT when a message arrives at subscribed actuator topics.
        Store the *latest* delta_<field> per actuator.
        Topic format: /<gh>/<rb>/actuators/<system>/<id>/data
        Expects payload like:
        {
          "id": "...",
          "delta_temperature": -0.0415,
          "delta_humidity": -0.4165,
          ...
        }
        """
        try:
            data = json.loads(
                payload.decode() if isinstance(payload, (bytes, bytearray)) else payload
            )
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
            # Correct: no argument
            self.mqtt.MyUnsubscribe()
        except Exception as e:
            logging.debug("[%s] Unsubscribe skipped: %s", self.device_id, e)
        super().stop()

    def _apply_and_clear_deltas(self, value):
        """
        Apply the sum of the *latest* deltas per actuator (if any) to the value being published.
        Deltas are NOT cleared: they represent actuators' current state.
        """
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
                    totals[field] = totals.get(field, 0.0) + dv
                    contrib_ids.setdefault(field, []).append(act_id)

        if not totals:
            return value

        # Dict case
        if isinstance(value, dict):
            out = dict(value)
            applied = {}
            for field, delta_sum in totals.items():
                if field in out:
                    try:
                        base = float(out[field])
                        new_val = base + float(delta_sum)
                        out[field] = new_val
                        applied[field] = {
                            "base": round(base, 4),
                            "new": round(new_val, 4),
                            "delta_sum": round(delta_sum, 4),
                            "contributors": len(set(contrib_ids.get(field, []))),
                            "actuators": sorted(set(contrib_ids.get(field, []))),
                        }
                    except (TypeError, ValueError):
                        pass
            if applied:
                logging.info(
                    "[%s] Applied latest-per-actuator deltas: %s",
                    self.device_id,
                    applied,
                )
            return out

        # Scalar case (single measurement)
        if len(self.measurements) == 1:
            m = self.measurements[0]
            field = m.get("field") if isinstance(m, dict) else str(m)
            delta_sum = totals.get(field)
            if delta_sum is not None:
                try:
                    base = float(value)
                    new_val = base + float(delta_sum)
                    ids = sorted(set(contrib_ids.get(field, [])))
                    logging.info(
                        "[%s] Applied latest-per-actuator delta on %s: base=%.4f, new=%.4f, "
                        "delta_sum=%.4f, contributors=%d, actuators=%s",
                        self.device_id,
                        field,
                        base,
                        new_val,
                        float(delta_sum),
                        len(ids),
                        ids,
                    )
                    return new_val
                except (TypeError, ValueError):
                    return value

        return value

    # Override to inject the deltas just-in-time
    def send_value(self, value):
        adjusted = self._apply_and_clear_deltas(value)
        super().send_value(adjusted)

    def read_value(self):
        self.loop(self._fake_read)

    def _fake_read(self):
        if len(self.measurements) == 1:
            m = self.measurements[0]
            return SimulateRealTimeReading(m).read()

        sensors = [m for m in self.measurements if m != "light_natural"]
        readings = {m: SimulateRealTimeReading(m).read() for m in sensors}
        return readings
