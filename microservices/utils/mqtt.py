import json
import logging
import paho.mqtt.client as mqtt


class MyMQTT:
    """Minimal MQTT wrapper: connect, (re)subscribe, publish, notify."""

    def __init__(self, clientID, broker, port, notifier):
        self._clientID = clientID
        self.broker = broker
        self.port = port
        self.notifier = notifier
        self._topic = None
        self._connected_once = False

        self._c = mqtt.Client(
            mqtt.CallbackAPIVersion.VERSION1, client_id=clientID, clean_session=True
        )
        self._c.on_connect = self._on_connect
        self._c.on_message = self._on_message
        self._c.on_disconnect = self._on_disconnect

        try:
            self._c.reconnect_delay_set(min_delay=1, max_delay=30)
        except Exception:
            pass

    # --- callbacks ---

    def _on_connect(self, client, userdata, flags, rc):
        logging.info(
            "[%s] Connected to %s:%s (rc=%s)",
            self._clientID,
            self.broker,
            self.port,
            rc,
        )
        if rc == 0 and self._connected_once and self._topic:
            self._c.subscribe(self._topic, qos=2)
            logging.info("[%s] Resubscribed to %s", self._clientID, self._topic)
        self._connected_once = True

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logging.warning("[%s] Unexpected disconnect (rc=%s)", self._clientID, rc)
        else:
            logging.info("[%s] Disconnected.", self._clientID)

    def _on_message(self, client, userdata, msg):
        try:
            self.notifier.notify(msg.topic, msg.payload or b"")
        except Exception:
            logging.exception("[%s] notifier.notify error", self._clientID)

    # --- api ---

    def start(self):
        logging.info(
            "[%s] Connecting to %s:%s ...", self._clientID, self.broker, self.port
        )
        self._c.connect(self.broker, self.port, keepalive=60)
        self._c.loop_start()

    def MySubscribe(self, topic):
        self._topic = topic
        self._c.subscribe(topic, qos=2)
        logging.info("[%s] Subscribed to %s", self._clientID, topic)

    def MyPublish(self, topic, message):
        try:
            payload = json.dumps(message, default=str)
        except Exception:
            logging.exception("[%s] json.dumps failed", self._clientID)
            return None
        info = self._c.publish(topic, payload, qos=2, retain=False) # Hardcoded to False
        rc = getattr(info, "rc", 0)
        if rc == 0:
            logging.info("[%s] Published to %s: %s", self._clientID, topic, payload)
        else:
            logging.warning(
                "[%s] Publish failed to %s (rc=%s)", self._clientID, topic, rc
            )
        return info

    def MyUnsubscribe(self):
        if self._topic:
            try:
                self._c.unsubscribe(self._topic)
                logging.info("[%s] Unsubscribed from %s", self._clientID, self._topic)
            except Exception:
                logging.exception("[%s] Unsubscribe error", self._clientID)

    def stop(self):
        self.MyUnsubscribe()
        try:
            self._c.loop_stop()
        except Exception:
            logging.exception("[%s] loop_stop error", self._clientID)
        try:
            self._c.disconnect()
        except Exception:
            logging.exception("[%s] disconnect error", self._clientID)