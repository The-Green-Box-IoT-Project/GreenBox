import json
import logging
from typing import Any, Dict, Tuple
from dataclasses import dataclass

from greenbox.utils.mqtt import MyMQTT
# Importa il modulo catalog_client in modo unificato
from greenbox.utils import catalog_client
from greenbox.controller.optimizer import Optimizer, LightOptimizer, PhMonitor


@dataclass
class ZoneOptimizers:
    """Contenitore per le istanze degli ottimizzatori di una singola zona (gh_id, rb_id)."""
    main: Optimizer
    light: LightOptimizer
    ph: PhMonitor


class Controller:
    """Bridge between statistics and actuators/alerts (multi-tenant, zone-aware)."""

    def __init__(self):
        # Chiama direttamente le funzioni necessarie invece di log_to_catalog
        broker_ip, broker_port = catalog_client.get_broker_info()
        self.broker = broker_ip
        self.port = broker_port

        self.clientID = "controller_all"
        self.mqtt = MyMQTT(
            self.clientID, broker=self.broker, port=self.port, notifier=self
        )

        # Cache per le istanze degli ottimizzatori, indicizzate per (greenhouse_id, raspberry_id)
        self.optimizer_cache: Dict[Tuple[str, str], ZoneOptimizers] = {}

        # Mappa per tenere traccia dello stato degli attuatori per zona (per evitare comandi ridondanti)
        self.last_actuator_commands: Dict[Tuple[str, str], Dict[str, Any]] = {}

    def start(self):
        # Il controller si iscrive ora ai topic di snapshot per ogni zona
        self.mqtt.start()
        # Topic: /{greenhouse_id}/{raspberry_id}/statistics/state
        self.mqtt.MySubscribe("/+/+/statistics/state")

    def stop(self):
        self.mqtt.stop()

    def _get_or_create_optimizers(self, gh_id: str, rb_id: str) -> ZoneOptimizers:
        """
        Recupera dalla cache o crea un nuovo set di ottimizzatori per la zona (gh_id, rb_id).
        """
        zone_key = (gh_id, rb_id)
        if zone_key in self.optimizer_cache:
            return self.optimizer_cache[zone_key]

        logging.info(
            "[%s] No optimizer found for zone '%s/%s'. Creating new instance...",
            self.clientID,
            gh_id,
            rb_id,
        )

        # Usa il catalog_client unificato per caricare le configurazioni
        thresholds = catalog_client.get_thresholds_config(gh_id)
        effects = catalog_client.get_effects_config(gh_id)

        # Crea le nuove istanze con le configurazioni caricate
        main_opt = Optimizer(
            thresholds_config=thresholds,
            effects_config_df=effects,
            weights={"energy": 1.0, "water": 1.0},
        )
        light_opt = LightOptimizer(
            thresholds_config=thresholds, effects_config_df=effects
        )
        ph_mon = PhMonitor(thresholds_config=thresholds)

        new_optimizers = ZoneOptimizers(main=main_opt, light=light_opt, ph=ph_mon)
        self.optimizer_cache[zone_key] = new_optimizers
        logging.info(
            "[%s] Successfully created optimizer instance for zone '%s/%s'.",
            self.clientID,
            gh_id,
            rb_id,
        )

        return new_optimizers

    def notify(self, topic: str, payload: str):
        """
        Gestisce i messaggi MQTT di stato aggregato per zona.
        Si aspetta un payload JSON completo per una specifica zona.
        """
        try:
            data = json.loads(payload)

            gh_id = data.get("greenhouse_id")
            rb_id = data.get("raspberry_id")

            if not (gh_id and rb_id):
                logging.warning(
                    "[%s] Missing 'greenhouse_id' or 'raspberry_id' in payload from topic %s.",
                    self.clientID,
                    topic,
                )
                return

            optimizers = self._get_or_create_optimizers(gh_id, rb_id)
            metrics_payload = data.get("metrics", {})
            zone_key = (gh_id, rb_id)
            current_actuator_state = self.last_actuator_commands.get(zone_key, {}) # Recupera l'ultimo stato noto
            
            # --- Gestione Ottimizzatore Principale ---
            res_main = optimizers.main.decide(metrics_payload, current_actuator_state=current_actuator_state)
            if res_main and res_main.get("mode") != "hold":
                actions = res_main.get("actions", {})
                
                if self.last_actuator_commands.get(zone_key) != actions:
                    self.last_actuator_commands[zone_key] = actions
                    for sys, lvl in actions.items():
                        if sys == "illumination_system":
                            continue
                            
                        cmd_topic = f"/{gh_id}/{rb_id}/actuators/{sys}/cmd"
                        msg = {
                            "cmd": "ON" if lvl > 0 else "OFF",
                            "level": lvl,
                        }
                        self.mqtt.MyPublish(cmd_topic, msg)
                else:
                    logging.debug("[%s] Zone %s/%s - Main optimizer actions unchanged.", self.clientID, gh_id, rb_id)

            # --- Gestione Ottimizzatore Luce ---
            light_data = metrics_payload.get("light")
            if light_data and isinstance(light_data, dict) and "median" in light_data:
                try:
                    res_light = optimizers.light.decide(float(light_data["median"]))
                    if res_light:
                        cmd_topic = f"/{gh_id}/{rb_id}/actuators/illumination_system/cmd"
                        self.mqtt.MyPublish(cmd_topic, res_light)
                except (ValueError, TypeError):
                    logging.warning("[%s] Zone %s/%s - Non-numeric median value for total light: %s", self.clientID, gh_id, rb_id, light_data)

            # --- Gestione Monitor PH ---
            ph_data = metrics_payload.get("ph")
            if ph_data and isinstance(ph_data, dict) and "median" in ph_data:
                try:
                    res_ph = optimizers.ph.decide(float(ph_data["median"]))
                    if res_ph:
                        alert_topic = f"/{gh_id}/{rb_id}/alerts/ph"
                        self.mqtt.MyPublish(alert_topic, res_ph)
                except (ValueError, TypeError):
                    logging.warning("[%s] Zone %s/%s - Non-numeric median value for ph: %s", self.clientID, gh_id, rb_id, ph_data)

        except Exception as e:
            logging.error(
                "[%s] Unhandled exception in notify for topic %s with payload %s: %s",
                self.clientID,
                topic,
                payload,
                e,
                exc_info=True,
            )