import pandas as pd
from pprint import pformat
from typing import Dict
from pathlib import Path
import json
import os
import time
import threading
import logging
from datetime import datetime, timezone
from utils.tools import load_dotenv
from utils.MyMQTT import MyMQTT
load_dotenv()

P = Path(__file__).parent.absolute()


class Actuators:
    """Base class loading configuration and effects data for actuators."""

    EFFECTS_PATH = P / "effects.csv"
    CONFIG_PATH = P / "config.json"

    def __init__(self):
        # Load effect definitions and configuration
        self.df_effects = pd.read_csv(self.EFFECTS_PATH)
        with open(self.CONFIG_PATH, "r") as f:
            config = json.load(f)

        self.broker_ip = config["broker_ip"]
        self.broker_port = config["broker_port"]
        self.device_uuid = config["device_uuid"]
        self.greenhouse_uuid = config["greenhouse_uuid"]
        self.raspberry_uuid = config["raspberry_uuid"]

        # TODO: remove when catalog connection is available
        self.greenhouse_uuid = os.getenv("GREENBOX_UUID", self.greenhouse_uuid)
        self.raspberry_uuid = os.getenv("RASPBERRY_UUID", self.raspberry_uuid)

        self.systems = sorted(self.df_effects["system"].dropna().unique().tolist())
        self.metrics = self.df_effects.drop(
            columns=["system", "level", "energy_consumption", "water_consumption"]
        ).columns.tolist()

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)


class Actuator(Actuators):
    """Generic actuator class handling MQTT communication and periodic publishing."""

    def __init__(self, system: str, publish_period_s: float = 5.0):
        super().__init__()
        self.system = system
        self.level = 0
        self.CMD_TOPIC = None
        self.DATA_TOPIC = None

        sys = self.df_effects[self.df_effects["system"] == system]
        del self.df_effects

        self.levels = sys["level"].astype(str).tolist()
        self._by_level: Dict[str, Dict[str, float]] = {
            str(r["level"]): r.drop(labels=["system", "level"]).dropna().to_dict()
            for _, r in sys.iterrows()
        }

        self.publish_period_s = float(publish_period_s)

        # Status
        self._is_on = False
        self._on_epoch = None

        # Publisher thread
        self._pub_thread = None
        self._stop_event = threading.Event()

        # MQTT wrapper (created in start())
        self.mqtt = None

    def apply(self, level: int, dt: float) -> Dict[str, float]:
        """Return actuator effects for 'level' and duration dt (s)."""
        key = f"{level}%"
        self.level = level
        eff = self._by_level[key]

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
        """Set the actuator level without applying effects."""
        self.level = level

    def build_cmd_topic(self, system, device_uuid) -> str:
        """Build MQTT command topic for this actuator."""
        return f"/{self.greenhouse_uuid}/{self.raspberry_uuid}/actuators/{system}/{device_uuid}/cmd"

    def build_data_topic(self, system, device_uuid) -> str:
        """Build MQTT data topic for this actuator."""
        return f"/{self.greenhouse_uuid}/{self.raspberry_uuid}/actuators/{system}/{device_uuid}/data"

    def start(self):
        """Start MQTT client and subscribe to command topic."""
        self.mqtt = MyMQTT(
            clientID=self.device_uuid,
            broker=self.broker_ip,
            port=self.broker_port,
            notifier=self,
        )
        self.mqtt.start()
        self.mqtt.MySubscribe(self.CMD_TOPIC)

    def shutdown(self):
        """Turn off, stop thread and disconnect MQTT."""
        self._turn_off()
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
                logging.info(f"[{self.device_uuid}] Invalid format (missing 'cmd'): {payload_str!r}")
                return

            cmd = str(obj["cmd"]).upper()
            level = obj.get("level", None)

            if cmd == "ON":
                if level is not None:
                    try:
                        level = int(float(level))
                    except (TypeError, ValueError):
                        logging.info(f"[{self.device_uuid}] Invalid 'level': {level!r}")
                        return
                self._turn_on(level)
            elif cmd == "OFF":
                self._turn_off()
            else:
                logging.info(f"[{self.device_uuid}] Unsupported 'cmd': {cmd!r}")
        except json.JSONDecodeError:
            logging.info(f"[{self.device_uuid}] Invalid JSON payload: {payload!r}")
        except Exception as e:
            logging.info(f"[{self.device_uuid}] Error in notify: {e}")

    def _turn_on(self, level: int = None):
        """Turn on actuator and start publishing thread."""
        if level is not None:
            prev = self.level
            self.set_level(level)
            if self._is_on:
                if self.level != prev:
                    self._on_epoch = time.time()
                    logging.info(f"[{self.device_uuid}] Level changed: {self.level}% (timer reset).")
                else:
                    logging.info(f"[{self.device_uuid}] Level unchanged ({self.level}%).")
                return

        if self._is_on:
            logging.info(f"[{self.device_uuid}] Already ON (level={self.level}%).")
            return

        self._is_on = True
        self._on_epoch = time.time()
        self._stop_event.clear()
        self._pub_thread = threading.Thread(
            target=self._publisher_loop, name=f"{self.device_uuid}-pub", daemon=True
        )
        self._pub_thread.start()
        logging.info(f"[{self.device_uuid}] State: ON (level={self.level}%). Publishing to {self.DATA_TOPIC}")

    def _turn_off(self):
        """Turn off actuator and stop publishing thread."""
        if not self._is_on:
            self.set_level(0)
            return
        self._is_on = False
        self._stop_event.set()
        if self._pub_thread and self._pub_thread.is_alive():
            self._pub_thread.join(timeout=2.0)
        self._pub_thread = None
        self._on_epoch = None
        self.set_level(0)
        logging.info(f"[{self.device_uuid}] State: OFF. Publishing stopped.")

    def _publisher_loop(self):
        """Loop for periodic data publishing."""
        next_ts = time.time()
        while not self._stop_event.is_set():
            now = time.time()
            elapsed = int(now - self._on_epoch) if self._on_epoch else 0
            ts_iso = datetime.now(timezone.utc).isoformat()
            effects = self.apply(self.level, elapsed)

            payload = {
                "id": self.device_uuid,
                "timestamp": ts_iso,
                "seconds_since_on": elapsed,
                "system": self.system,
                "level": self.level,
            } | effects

            try:
                self.mqtt.MyPublish(self.DATA_TOPIC, payload)
            except Exception as e:
                logging.info(f"[{self.device_uuid}] Publish error: {e}")

            next_ts += self.publish_period_s
            delay = max(0.0, next_ts - time.time())
            if self._stop_event.wait(timeout=delay):
                break
