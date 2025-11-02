import json
import time
import logging
import threading
from typing import Dict
from pprint import pformat
from datetime import datetime, timezone

from greenbox.utils.catalog_client import log_to_catalog
from greenbox.utils.mqtt import MyMQTT
from greenbox.sim.effects.effects import Effects


class ActuatorConnector:
    def __init__(self):
        # GET from catalog
        cfg = log_to_catalog()
        self.greenhouse_id = cfg["greenhouse_id"]  # e.g. 'gh-01'
        raspberry_id = cfg["raspberry_id"]  # e.g. 'rb-01'
        broker_ip = cfg["broker_ip"]  # '127.0.0.1'
        broker_port = cfg["broker_port"]  # 1883
        associated_actuators = cfg["actuators"]
        topic = f"{self.greenhouse_id}/{raspberry_id}/actuators"

        self.actuators = [Actuator(a, broker_ip, broker_port, topic) for a in associated_actuators]

    def start(self):
        """Start all actuators."""
        for a in self.actuators:
            a.start()

    def stop(self):
        """Stop all actuators gracefully."""
        for a in self.actuators:
            a.turn_off()
            a.stop()


class Actuator:
    """Generic actuator class handling MQTT communication and periodic publishing."""

    def __init__(self, config_dict, broker_ip, broker_port, base_topic):
        self.device_id = config_dict['id']
        self.device_name = config_dict['name']
        self.system = config_dict['type']

        # Load effects
        effects = Effects()
        effects.get_system(self.system)
        self.levels = effects.levels
        self.by_level = effects.by_level

        # Prepare topics
        self.base_topic = base_topic.strip("/")
        self.CMD_TOPIC = self.build_cmd_topic(self.system, self.device_id)
        self.DATA_TOPIC = self.build_data_topic(self.system, self.device_id)

        # MQTT wrapper
        self.mqtt = MyMQTT(
            clientID=self.device_id,
            broker=broker_ip,
            port=broker_port,
            notifier=self,
        )

        # Status
        self.level = 0
        self.publish_period_s = 5.0
        self._is_on = False
        self._on_epoch = None
        self._stop_event = threading.Event()
        self._pub_thread = None
        self._lock = threading.Lock()

    def apply(self, level: int, dt: float) -> Dict[str, float]:
        """Return actuator effects for 'level' and duration dt (s)."""
        key = f"{level}%"
        eff = self.by_level[key]
        out = {}
        for k, v in eff.items():
            if k in ("energy_consumption", "water_consumption"):
                out[k] = v
            elif k == "light":
                out[f"delta_{k}"] = v
            else:
                out[f"delta_{k}"] = v * dt
        return out

    def set_level(self, level: int):
        """Set the actuator level."""
        self.level = level

    def build_cmd_topic(self, system, device_id) -> str:
        """Build MQTT command topic for this actuator."""
        return f"/{self.base_topic}/{system}/{device_id}/cmd"

    def build_data_topic(self, system, device_id) -> str:
        """Build MQTT data topic for this actuator."""
        return f"/{self.base_topic}/{system}/{device_id}/data"

    def start(self):
        """Start MQTT client and subscribe to command topic."""
        self.mqtt.start()
        self.mqtt.MySubscribe(self.CMD_TOPIC)
        logging.info(f"[{self.device_id}] Listening on {self.CMD_TOPIC}")

    def stop(self):
        """Turn off and disconnect MQTT."""
        try:
            self.mqtt.MyUnsubscribe(self.CMD_TOPIC)
        except Exception:
            pass
        self.mqtt.stop()

    def notify(self, topic, payload):
        """Handle received MQTT command messages."""
        try:
            payload_str = (
                payload.decode("utf-8", errors="ignore")
                if isinstance(payload, (bytes, bytearray))
                else str(payload)
            )
            obj = json.loads(payload_str)
            if not isinstance(obj, dict) or "cmd" not in obj:
                logging.info(f"[{self.device_id}] Invalid format: {payload_str!r}")
                return

            cmd = str(obj["cmd"]).upper()
            level = obj.get("level", None)

            if cmd == "ON":
                if level is not None:
                    try:
                        level = int(float(level))
                    except (TypeError, ValueError):
                        logging.info(f"[{self.device_id}] Invalid 'level': {level!r}")
                        return
                self._turn_on(level)
            elif cmd == "OFF":
                self.turn_off()
            else:
                logging.info(f"[{self.device_id}] Unsupported 'cmd': {cmd!r}")

        except json.JSONDecodeError:
            logging.info(f"[{self.device_id}] Invalid JSON payload: {payload!r}")
        except Exception as e:
            logging.info(f"[{self.device_id}] Error in notify: {e}")

    def _turn_on(self, level: int = None):
        """Turn on actuator and start publisher thread."""
        with self._lock:
            if level is not None:
                prev = self.level
                self.set_level(level)
                if self._is_on and self.level != prev:
                    self._on_epoch = time.time()
                    logging.info(f"[{self.device_id}] Level changed to {self.level}%.")
                    return

            if self._is_on:
                logging.info(f"[{self.device_id}] Already ON.")
                return

            self._is_on = True
            self._on_epoch = time.time()
            self._stop_event.clear()
            self._pub_thread = threading.Thread(
                target=self._publisher_loop, name=f"{self.device_id}-pub", daemon=True
            )
            self._pub_thread.start()
            logging.info(f"[{self.device_id}] State: ON (level={self.level}%).")

    def turn_off(self):
        """Turn off actuator and stop publishing thread."""
        with self._lock:
            if not self._is_on:
                self.set_level(0)
                return
            self._is_on = False
            self._stop_event.set()
        if self._pub_thread and self._pub_thread.is_alive():
            self._pub_thread.join(timeout=2.0)
        self._pub_thread = None
        with self._lock:
            self._on_epoch = None
            self.set_level(0)
        logging.info(f"[{self.device_id}] State: OFF. Publishing stopped.")

    def _publisher_loop(self):
        """Periodic data publishing loop."""
        next_ts = time.time()
        last_ts = next_ts
        while not self._stop_event.is_set():
            now = time.time()
            dt = now - last_ts
            last_ts = now
            with self._lock:
                elapsed = int(now - self._on_epoch) if self._on_epoch else 0
                lvl = self.level
            effects = self.apply(lvl, dt)
            ts_iso = datetime.now(timezone.utc).isoformat()
            payload = {
                "id": self.device_id,
                "timestamp": ts_iso,
                "seconds_since_on": elapsed,
                "system": self.system,
                "level": lvl,
            } | effects
            try:
                self.mqtt.MyPublish(self.DATA_TOPIC, payload)
            except Exception as e:
                logging.info(f"[{self.device_id}] Publish error: {e}")

            next_ts += self.publish_period_s
            delay = max(0.0, next_ts - time.time())
            if self._stop_event.wait(timeout=delay):
                break

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)
