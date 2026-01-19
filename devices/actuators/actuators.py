import os
import json
import logging
import threading
from typing import Dict
from pprint import pformat
from dotenv import load_dotenv

load_dotenv()

from devices.utils.mqtt import MyMQTT
from devices.utils.client import get_effects_config


class Actuator:
    """
    Represents a single, independent actuator instance.
    It connects to MQTT, listens for commands on its specific topic,
    and publishes its simulated state. It uses the global logger,
    which is configured by the script that launches it.
    """

    def __init__(
        self,
        device_id: str,
        system: str,
        gh_id: str,
        rb_id: str,
        broker_ip: str,
        broker_port: int,
    ):
        self.device_id = device_id
        self.system = system
        self.gh_id = gh_id
        self.rb_id = rb_id

        # Load the simulation model (effects) for this actuator's system type
        effects_df = get_effects_config()
        actuator_effects_df = effects_df[effects_df["system"] == self.system].copy()
        if actuator_effects_df.empty:
            logging.warning(
                "[%s] No effects configuration found for system '%s'. This actuator will have no simulated effect.",
                self.device_id,
                self.system,
            )

        self.levels = sorted(actuator_effects_df["level"].astype(str).tolist())
        self.by_level: Dict[str, Dict[str, float]] = {
            str(r["level"]): r.drop(labels=["system", "level"]).dropna().to_dict()
            for _, r in actuator_effects_df.iterrows()
        }

        # Keep the list of "effect" fields to always publish delta_* (also when OFF)
        self.effect_fields = [
            c
            for c in actuator_effects_df.columns
            if c not in ("system", "level", "energy_consumption", "water_consumption")
        ]

        # Build zone-specific topics
        self.CMD_TOPIC = f"/{self.gh_id}/{self.rb_id}/actuators/{self.system}/cmd"
        self.DATA_TOPIC = (
            f"/{self.gh_id}/{self.rb_id}/actuators/{self.system}/{self.device_id}/data"
        )

        # MQTT wrapper
        self.mqtt = MyMQTT(
            clientID=self.device_id,
            broker=broker_ip,
            port=broker_port,
            notifier=self,
        )

        # Status
        self.level = 0
        self.publish_period_s = float(os.getenv("TIME_INTERVAL_SENSORS", "5"))
        self._is_on = False
        self._stop_event = threading.Event()
        self._pub_thread = None
        self._lock = threading.Lock()

    def apply(self, level: int, dt: float, is_on: bool) -> Dict[str, float]:
        """
        Calculates the simulated *per-step* effect of the actuator for the next interval dt.
        For light, the effect is a constant output (not multiplied by dt).
        Always emits delta_* keys (0.0 when OFF) to avoid stale deltas on sensors.
        """
        key = f"{level}%"
        eff = self.by_level.get(key, self.by_level.get(str(level), {}))

        out: Dict[str, float] = {}

        # energy/water are published as configured (kept simple)
        try:
            out["energy_consumption"] = float(eff.get("energy_consumption", 0.0) or 0.0)
        except (TypeError, ValueError):
            out["energy_consumption"] = 0.0

        try:
            out["water_consumption"] = float(eff.get("water_consumption", 0.0) or 0.0)
        except (TypeError, ValueError):
            out["water_consumption"] = 0.0

        # If OFF or level=0, publish deltas as 0.0
        if not is_on or level <= 0:
            for k in self.effect_fields:
                out[f"delta_{k}"] = 0.0
            return out

        # ON: compute per-step deltas
        for k in self.effect_fields:
            v = eff.get(k, 0.0)
            try:
                v = float(v or 0.0)
            except (TypeError, ValueError):
                v = 0.0

            if k == "light":
                out[f"delta_{k}"] = v
            else:
                out[f"delta_{k}"] = v * float(dt)

        return out

    def set_level(self, level: int):
        self.level = level

    def start(self):
        """Start MQTT client and subscribe to command topic."""
        self.mqtt.start()
        self.mqtt.MySubscribe(self.CMD_TOPIC)
        logging.info(f"[{self.device_id}] Listening on {self.CMD_TOPIC}")
        # Start publisher thread immediately (publish even at level=0)
        with self._lock:
            if self._pub_thread is None or not self._pub_thread.is_alive():
                self._stop_event.clear()
                self._pub_thread = threading.Thread(
                    target=self._publisher_loop,
                    name=f"{self.device_id}-pub",
                    daemon=True,
                )
                self._pub_thread.start()

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
                        logging.warning(
                            f"[{self.device_id}] Invalid 'level': {level!r}"
                        )
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

    def _publish_now(self):
        """
        Publish immediately current actuator state (level + delta_*) so sensors stop using stale deltas.
        """
        with self._lock:
            lvl = self.level
            is_on = self._is_on and lvl > 0

        effects = self.apply(lvl, self.publish_period_s, is_on)

        payload = {
            "id": self.device_id,
            "system": self.system,
            "level": lvl,
        } | effects

        payload.setdefault("water_consumption", 0.0)
        payload.setdefault("energy_consumption", 0.0)

        try:
            self.mqtt.MyPublish(self.DATA_TOPIC, payload)
        except Exception as e:
            logging.warning(f"[{self.device_id}] Publish error: {e}")

    def _turn_on(self, level: int):
        publish_needed = False

        with self._lock:
            prev = self.level
            self.set_level(level)

            if self._is_on and self.level != prev:
                logging.info(f"[{self.device_id}] Level changed to {self.level}%.")
                publish_needed = True

            elif not self._is_on:
                self._is_on = True
                logging.info(f"[{self.device_id}] State: ON (level={self.level}%).")
                publish_needed = True

        # Pubblica fuori dal lock per evitare deadlock (Lock non re-entrante)
        if publish_needed:
            self._publish_now()

    def turn_off(self):
        with self._lock:
            self._is_on = False
            self.set_level(0)

        logging.info(f"[{self.device_id}] State: OFF.")
        # Pubblica fuori dal lock per evitare deadlock
        self._publish_now()

    def _publisher_loop(self):
        """Periodic data publishing loop."""
        while not self._stop_event.is_set():
            with self._lock:
                lvl = self.level
                is_on = self._is_on and lvl > 0

            effects = self.apply(lvl, self.publish_period_s, is_on)

            payload = {
                "id": self.device_id,
                "system": self.system,
                "level": lvl,
            } | effects

            # Ensure keys always present
            payload.setdefault("water_consumption", 0.0)
            payload.setdefault("energy_consumption", 0.0)

            try:
                self.mqtt.MyPublish(self.DATA_TOPIC, payload)
            except Exception as e:
                logging.warning(f"[{self.device_id}] Publish error: {e}")

            if self._stop_event.wait(timeout=self.publish_period_s):
                break

    def __str__(self):
        return pformat(self.__dict__, indent=1, sort_dicts=False)
