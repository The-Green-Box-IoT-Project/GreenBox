import os
import json
import time
import threading
import logging
import hashlib

from pymongo import MongoClient
from utils.mqtt import MyMQTT


class Notifier:
    """
    Polls MongoDB for zones.strategy changes and publishes MQTT events.
    Practical: no replica set, no keyfile, works with docker compose up/down.
    """

    def __init__(self):
        self.mongo_uri = os.environ["MONGO_URI"]
        self.mongo_db = os.environ.get("MONGO_DB", "greenbox")

        self.broker_ip = os.environ["BROKER_IP"]
        self.broker_port = int(os.environ.get("BROKER_PORT", "1883"))

        self.client_id = os.environ.get("NOTIFIER_CLIENT_ID", "mongo_strategy_notifier")
        self.poll_s = float(os.environ.get("STRATEGY_POLL_S", "1.0"))

        self._stop = threading.Event()
        self._thread = None

        # cache: zone_id -> md5(strategy_json)
        self._sig = {}

        # Use your wrapper (notifier is not needed for publish-only)
        self.mqtt = MyMQTT(
            clientID=self.client_id,
            broker=self.broker_ip,
            port=self.broker_port,
            notifier=None,
        )

    @staticmethod
    def _hash_strategy(strategy) -> str:
        try:
            s = json.dumps(strategy or {}, sort_keys=True, separators=(",", ":"))
        except Exception:
            s = "{}"
        return hashlib.md5(s.encode("utf-8")).hexdigest()

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()

        # connect mqtt once
        try:
            self.mqtt.start()
        except Exception as e:
            logging.warning("[notifier] MQTT start failed (will retry in loop): %s", e)

        self._thread = threading.Thread(
            target=self._run, name="strategy-poll-notifier", daemon=True
        )
        self._thread.start()
        logging.info("[notifier] started (poll_s=%s)", self.poll_s)

    def stop(self):
        self._stop.set()
        try:
            self.mqtt.stop()
        except Exception:
            pass

    def _run(self):
        client = MongoClient(self.mongo_uri)
        db = client[self.mongo_db]
        zones = db["zones"]

        while not self._stop.is_set():
            try:
                cursor = zones.find({}, {"_id": 0, "zone_id": 1, "strategy": 1})
                for doc in cursor:
                    zone_id = doc.get("zone_id")
                    if not zone_id:
                        continue

                    strategy = doc.get("strategy", {})
                    new_sig = self._hash_strategy(strategy)
                    old_sig = self._sig.get(zone_id)

                    # First time: initialize cache (and optionally publish retained snapshot)
                    if old_sig is None:
                        self._sig[zone_id] = new_sig
                        payload = {
                            "event": "strategy_snapshot",
                            "zone_id": zone_id,
                            "strategy": strategy,
                            "ts": time.time(),
                        }
                        topic = f"/zones/{zone_id}/strategy/updated"
                        self.mqtt.MyPublish(topic, payload)
                        continue

                    if new_sig != old_sig:
                        self._sig[zone_id] = new_sig
                        payload = {
                            "event": "strategy_updated",
                            "zone_id": zone_id,
                            "strategy": strategy,
                            "ts": time.time(),
                        }
                        topic = f"/zones/{zone_id}/strategy/updated"
                        self.mqtt.MyPublish(topic, payload)

            except Exception as e:
                logging.warning("[notifier] poll error: %s", e)

            if self._stop.wait(self.poll_s):
                break
