# controller.py
from __future__ import annotations
import json
import logging
from pathlib import Path
from typing import Any, Dict

from utils.MyMQTT import MyMQTT
from Optimizer.optimizer.optimizer import Optimizer
from Optimizer.optimizer.light_optimizer import LightOptimizer
from Optimizer.optimizer.ph_monitor import PhMonitor
from Actuators.actuator.actuator import Actuators

P = Path(__file__).parent
DEVICE_MAP_PATH = P / "device_map.json"


class Controller:
    """Bridge between statistics and actuators/alerts."""

    def __init__(self):
        # Base info (broker, UUIDs)
        base = Actuators()
        self.broker = base.broker_ip
        self.port = base.broker_port
        self.greenhouse_uuid = base.greenhouse_uuid
        self.raspberry_uuid = base.raspberry_uuid

        # Load device map (system → device_uuid)
        self.device_map = self._load_device_map(DEVICE_MAP_PATH)

        self.clientID = "controller"
        self.mqtt = MyMQTT(self.clientID, broker=self.broker, port=self.port, notifier=self)

        # Optimizers / monitors
        self.opt = Optimizer(weights={"energy": 1.0, "water": 1.0})
        self.light = LightOptimizer()
        self.ph = PhMonitor()

        self.latest_stats: Dict[str, Dict[str, Any]] = {}

    def start(self):
        self.mqtt.start()
        topic = f"/{self.greenhouse_uuid}/{self.raspberry_uuid}/statistics/#"
        self.mqtt.MySubscribe(topic)

    def stop(self):
        self.mqtt.stop()

    def notify(self, topic: str, payload: str):
        try:
            data = json.loads(payload)
        except Exception:
            logging.warning(f"[{self.clientID}] Invalid JSON on {topic}")
            return

        if "/statistics/light_natural" in topic:
            self._handle_light(data)
        elif "/statistics/ph" in topic:
            self._handle_ph(data)
        elif "/statistics/" in topic:
            self._handle_env(data)

    def _handle_env(self, data: Dict[str, Any]):
        metric = data.get("metric")
        if not metric:
            return
        self.latest_stats[metric] = data

        res = self.opt.decide(self.latest_stats)
        if res["mode"] == "hold":
            return

        duration = res.get("duration_s", 0.0)
        for sys, lvl in res["actions"].items():
            dev_uuid = self.device_map.get(sys)
            if not dev_uuid:
                logging.warning(f"[{self.clientID}] Missing device_uuid for system '{sys}' in device_map.json")
                continue

            topic = f"/{self.greenhouse_uuid}/{self.raspberry_uuid}/actuators/{sys}/{dev_uuid}/cmd"
            msg = {"cmd": "ON" if lvl > 0 else "OFF", "level": lvl, "duration_s": duration}
            self.mqtt.MyPublish(topic, msg)

    def _handle_light(self, data: Dict[str, Any]):
        median = data.get("median")
        if median is None:
            return
        res = self.light.decide(float(median))
        if res:
            dev_uuid = self.device_map.get("illumination_system")
            if not dev_uuid:
                logging.warning(f"[{self.clientID}] Missing 'illumination_system' in device_map.json")
                return
            topic = f"/{self.greenhouse_uuid}/{self.raspberry_uuid}/actuators/illumination_system/{dev_uuid}/cmd"
            self.mqtt.MyPublish(topic, res)

    def _handle_ph(self, data: Dict[str, Any]):
        median = data.get("median")
        if median is None:
            return
        res = self.ph.decide(float(median))
        if res:
            alert = {"msg": res["message"]}
            topic = f"/{self.greenhouse_uuid}/{self.raspberry_uuid}/alerts/ph"
            self.mqtt.MyPublish(topic, alert)

    @staticmethod
    def _load_device_map(path: Path) -> Dict[str, str]:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
