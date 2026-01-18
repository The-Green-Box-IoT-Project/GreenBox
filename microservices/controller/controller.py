import datetime
import os
import pandas as pd
import json
from typing import Any, Dict, Tuple
from dataclasses import dataclass
from zoneinfo import ZoneInfo

LOCAL_TZ = ZoneInfo("Europe/Rome")

from utils.threshold import Threshold
from utils.mqtt import MyMQTT
from optimizer import Optimizer, LightOptimizer
from utils.client import get_thresholds, get_device_context


@dataclass
class ZoneOptimizers:
    """Contenitore per le istanze degli ottimizzatori di una singola zona (gh_id, rb_id)."""

    main: Optimizer
    light: LightOptimizer
    light_enabled: bool
    light_start_hour: int
    light_end_hour: int


class Controller:
    """Bridge between statistics and actuators/alerts (multi-tenant, zone-aware)."""

    def __init__(self):
        # Recupera le informazioni del broker dalle variabili d'ambiente
        self.broker = os.environ["BROKER_IP"]
        self.port = int(os.environ["BROKER_PORT"])

        self.clientID = "controller_all"
        self.mqtt = MyMQTT(
            self.clientID, broker=self.broker, port=self.port, notifier=self
        )

        # Cache per le istanze degli ottimizzatori, indicizzate per (greenhouse_id, raspberry_id)
        self.optimizer_cache: Dict[Tuple[str, str], ZoneOptimizers] = {}

        # Mappa (gh_id, rb_id) -> zone_id (per invalidare la cache su eventi strategy)
        self.device_zone_map: Dict[Tuple[str, str], str] = {}

        # Mappa per tenere traccia dello stato degli attuatori per zona (per evitare comandi ridondanti)
        self.last_actuator_commands: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def start(self):
        self.mqtt.start()
        # Topic: /{greenhouse_id}/{raspberry_id}/statistics/state
        self.mqtt.MySubscribe("/+/+/statistics/state")
        # Topic per aggiornamenti di strategia (per invalidare la cache)
        self.mqtt.MySubscribe("/zones/+/strategy/updated")

    def stop(self):
        self.mqtt.stop()

    def _get_or_create_optimizers(self, gh_id: str, rb_id: str) -> ZoneOptimizers:
        """
        Recupera dalla cache o crea un nuovo set di ottimizzatori per la zona (gh_id, rb_id).
        """
        zone_key = (gh_id, rb_id)
        if zone_key in self.optimizer_cache:
            return self.optimizer_cache[zone_key]

        print(
            f"[{self.clientID}] No optimizer found for zone '{gh_id}/{rb_id}'. Creating new instance..."
        )

        username, zone_id = None, None
        device_context = get_device_context(gh_id, rb_id)
        if device_context:
            username = device_context.get("username")
            zone_id = device_context.get("zone_id")
        if not (username and zone_id):
            raise ValueError(
                f"Cannot create optimizer: Unable to find username/zone_id for device '{rb_id}' in greenhouse '{gh_id}'."
            )

        thresholds_from_catalog = get_thresholds(username, zone_id)
        effects = pd.read_csv("./effects/effects.csv")

        # Converte il formato delle soglie e gestisce la configurazione della luce
        thresholds: Dict[str, Threshold] = {}
        light_enabled = False
        light_start_hour = 0
        light_end_hour = 0
        light_config = thresholds_from_catalog.get("light", {})

        if light_config.get("enabled") == "true":
            light_enabled = True
            light_start_hour = int(light_config.get("start", 0))
            light_end_hour = int(light_config.get("end", 0))
            # Usa una soglia fissa letta da variabili d'ambiente
            light_lux_threshold = float(os.environ["LIGHT_LUX_THRESHOLD"])
            thresholds["light"] = Threshold(
                lower=light_lux_threshold, upper=1_000_000.0
            )
        else:
            # Placeholder per evitare crash del LightOptimizer quando la luce è disabilitata
            thresholds["light"] = Threshold(lower=0.0, upper=0.0)

        for metric, values in thresholds_from_catalog.items():
            if metric != "light":
                thresholds[metric] = Threshold(
                    lower=float(values["min"]), upper=float(values["max"])
                )

        # Crea le nuove istanze con le configurazioni caricate
        main_opt = Optimizer(
            thresholds_config=thresholds,
            effects_config_df=effects,
            weights={"energy": 1.0, "water": 1.0},
        )
        light_opt = LightOptimizer(
            thresholds_config=thresholds, effects_config_df=effects
        )

        new_optimizers = ZoneOptimizers(
            main=main_opt,
            light=light_opt,
            light_enabled=light_enabled,
            light_start_hour=light_start_hour,
            light_end_hour=light_end_hour,
        )

        self.optimizer_cache[zone_key] = new_optimizers
        # IMPORTANT: salva mapping (gh_id, rb_id) -> zone_id per invalidazione cache su eventi strategy
        self.device_zone_map[zone_key] = zone_id

        print(
            f"[{self.clientID}] Successfully created optimizer instance for zone '{gh_id}/{rb_id}'."
        )

        return new_optimizers

    def notify(self, topic: str, payload: str):
        """
        Gestisce i messaggi MQTT di stato aggregato per zona.
        Si aspetta un payload JSON completo per una specifica zona.
        """
        try:
            payload_str = (
                payload.decode("utf-8", errors="ignore")
                if isinstance(payload, (bytes, bytearray))
                else str(payload)
            )
            data = json.loads(payload_str)

            # --- Eventi strategy update (da mongo-adapter) ---
            if topic.startswith("/zones/") and topic.endswith("/strategy/updated"):
                zone_id = data.get("zone_id")
                if not zone_id:
                    print(
                        f"WARNING: [{self.clientID}] Missing 'zone_id' in payload from topic {topic}."
                    )
                    return

                # invalida tutte le zone_key che puntano a quel zone_id
                keys = [k for k, z in self.device_zone_map.items() if z == zone_id]
                if not keys:
                    print(
                        f"DEBUG: [{self.clientID}] Strategy update for {zone_id}, but no cached device matched."
                    )
                    return

                for k in keys:
                    self.optimizer_cache.pop(k, None)
                    self.last_actuator_commands.pop(k, None)
                    self.device_zone_map.pop(k, None)

                print(
                    f"[{self.clientID}] Strategy updated for {zone_id} -> invalidated {len(keys)} optimizer(s)."
                )
                return

            gh_id = data.get("greenhouse_id")
            rb_id = data.get("raspberry_id")

            if not (gh_id and rb_id):
                print(
                    f"WARNING: [{self.clientID}] Missing 'greenhouse_id' or 'raspberry_id' in payload from topic {topic}."
                )
                return

            optimizers = self._get_or_create_optimizers(gh_id, rb_id)
            metrics_payload = data.get("metrics", {})

            # normalizza humidity/soil_humidity da % (0..100) a frazione (0..1) se necessario
            for m in ("humidity", "soil_humidity"):
                md = metrics_payload.get(m)
                if isinstance(md, dict) and "median" in md:
                    try:
                        v = float(md["median"])
                        if v > 1.0:
                            v = v / 100.0
                        if v < 0.0:
                            v = 0.0
                        elif v > 1.0:
                            v = 1.0
                        md["median"] = round(v, 3)
                    except (ValueError, TypeError):
                        pass

            zone_key = (gh_id, rb_id)
            current_actuator_state = self.last_actuator_commands.get(zone_key, {})

            # --- Gestione Ottimizzatore Principale ---
            res_main = optimizers.main.decide(
                metrics_payload, current_actuator_state=current_actuator_state
            )

            if res_main:
                # Se tutto è in range, spegni tutto (level=0)
                if res_main.get("mode") == "hold":
                    actions = {sys: 0 for sys in optimizers.main.actuators}
                else:
                    actions = res_main.get("actions", {})

                if self.last_actuator_commands.get(zone_key) != actions:
                    self.last_actuator_commands[zone_key] = actions
                    print(
                        f"[{self.clientID}] Zone {gh_id}/{rb_id} actions -> {actions}"
                    )
                    for sys, lvl in actions.items():
                        if sys == "illumination_system":
                            continue

                        cmd_topic = f"/{gh_id}/{rb_id}/actuators/{sys}/cmd"
                        msg = {"cmd": "ON" if lvl > 0 else "OFF", "level": lvl}
                        self.mqtt.MyPublish(cmd_topic, msg)
                else:
                    print(
                        f"DEBUG: [{self.clientID}] Zone {gh_id}/{rb_id} - Main optimizer actions unchanged."
                    )

            # --- Gestione Ottimizzatore Luce ---
            if optimizers.light_enabled:
                current_hour = datetime.datetime.now(LOCAL_TZ).hour
                if (
                    optimizers.light_start_hour
                    <= current_hour
                    < optimizers.light_end_hour
                ):
                    light_data = metrics_payload.get("light")
                    if (
                        light_data
                        and isinstance(light_data, dict)
                        and "median" in light_data
                    ):
                        try:
                            res_light = optimizers.light.decide(
                                float(light_data["median"])
                            )
                            if res_light:
                                cmd_topic = f"/{gh_id}/{rb_id}/actuators/illumination_system/cmd"
                                self.mqtt.MyPublish(cmd_topic, res_light)
                        except (ValueError, TypeError):
                            print(
                                f"WARNING: [{self.clientID}] Zone {gh_id}/{rb_id} - Non-numeric median value for total light: {light_data}"
                            )

        except Exception as e:
            print(
                f"ERROR: [{self.clientID}] Unhandled exception in notify for topic {topic} with payload {payload}: {e}"
            )
