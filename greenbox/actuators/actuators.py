import json
import time
import logging
import threading
from typing import Dict, List
from pathlib import Path
from pprint import pformat
from datetime import datetime, timezone

import pandas as pd
from greenbox.utils.mqtt import MyMQTT
from greenbox.utils import catalog_client

class Actuator:
    """
    Represents a single, independent actuator instance.
    It connects to MQTT, listens for commands on its specific topic,
    and publishes its simulated state. It uses the global logger,
    which is configured by the script that launches it.
    """

    def __init__(self, device_id: str, system: str, gh_id: str, rb_id: str, broker_ip: str, broker_port: int):
        self.device_id = device_id
        self.system = system
        self.gh_id = gh_id
        self.rb_id = rb_id

        # Load the simulation model (effects) for this actuator's system type
        effects_df = catalog_client.get_effects_config(gh_id)
        actuator_effects_df = effects_df[effects_df["system"] == self.system].copy()
        if actuator_effects_df.empty:
            logging.warning("[%s] No effects configuration found for system '%s'. This actuator will have no simulated effect.", self.device_id, self.system)
        
        self.levels = sorted(actuator_effects_df["level"].astype(str).tolist())
        self.by_level: Dict[str, Dict[str, float]] = {
            str(r["level"]): r.drop(labels=["system", "level"]).dropna().to_dict()
            for _, r in actuator_effects_df.iterrows()
        }

        # Build zone-specific topics
        self.CMD_TOPIC = f"/{self.gh_id}/{self.rb_id}/actuators/{self.system}/cmd"
        self.DATA_TOPIC = f"/{self.gh_id}/{self.rb_id}/actuators/{self.system}/{self.device_id}/data"

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

    def apply(self, level: int, elapsed_time: float) -> Dict[str, float]: # Modified signature
        """Calculates the simulated cumulative effect of the actuator since it was turned on."""
        key = f"{level}%"
        eff = self.by_level.get(key, self.by_level.get(str(level), {}))
        out = {}
        for k, v in eff.items():
            if k in ("energy_consumption", "water_consumption"):
                out[k] = v
            elif k == "light":
                # For light, the effect is a constant output, not cumulative over time.
                out[f"delta_{k}"] = v # Not multiplied by elapsed_time
            else:
                out[f"delta_{k}"] = v * elapsed_time # Multiplied by elapsed_time
        return out

    def set_level(self, level: int):
        self.level = level

    def start(self):
        """Start MQTT client and subscribe to command topic."""
        self.mqtt.start()
        self.mqtt.MySubscribe(self.CMD_TOPIC)
        logging.info(f"[{self.device_id}] Listening on {self.CMD_TOPIC}")

    def stop(self):
        """Gracefully stop the actuator."""
        logging.info(f"[{self.device_id}] Stop request received.")
        self.turn_off()
        try:
            self.mqtt.MyUnsubscribe(self.CMD_TOPIC)
        except Exception:
            pass
        self.mqtt.stop()
        logging.info(f"[{self.device_id}] Stopped.")


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
                logging.warning(f"[{self.device_id}] Invalid format: {payload_str!r}")
                return

            cmd = str(obj["cmd"]).upper()
            level = obj.get("level", None)

            if cmd == "ON":
                if level is not None:
                    try:
                        level = int(float(level))
                    except (TypeError, ValueError):
                        logging.warning(f"[{self.device_id}] Invalid 'level': {level!r}")
                        return
                self._turn_on(level)
            elif cmd == "OFF":
                self.turn_off()
            else:
                logging.warning(f"[{self.device_id}] Unsupported 'cmd': {cmd!r}")

        except json.JSONDecodeError:
            logging.warning(f"[{self.device_id}] Invalid JSON payload: {payload!r}")
        except Exception as e:
            logging.error(f"[{self.device_id}] Error in notify: {e}", exc_info=True)

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
        # next_ts = time.time() # No longer needed for elapsed calculation
        # last_ts = next_ts # No longer needed for elapsed calculation
        while not self._stop_event.is_set():
            now = time.time()
            # dt = now - last_ts # No longer needed
            # last_ts = now # No longer needed
            with self._lock:
                elapsed = int(now - self._on_epoch) if self._on_epoch else 0
                lvl = self.level
            effects = self.apply(lvl, float(elapsed)) # Pass elapsed as float
            ts_iso = datetime.now(timezone.utc).isoformat()
            payload = {
                "id": self.device_id,
                "timestamp": ts_iso,
                "seconds_since_on": elapsed,
                "system": self.system,
                "level": lvl,
            } | effects
            # Ensure water_consumption is always present, defaulting to 0.0 if not provided by effects
            payload.setdefault("water_consumption", 0.0)
            try:
                self.mqtt.MyPublish(self.DATA_TOPIC, payload)
            except Exception as e:
                logging.warning(f"[{self.device_id}] Publish error: {e}")

            # next_ts += self.publish_period_s # No longer needed if using sleep
            # delay = max(0.0, next_ts - time.time()) # No longer needed
            if self._stop_event.wait(timeout=self.publish_period_s): # Simplified sleep
                break

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)