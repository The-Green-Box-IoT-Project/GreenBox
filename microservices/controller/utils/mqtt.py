import json
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
        msg = "[%s] Connected to %s:%s (rc=%s)" % (
            self._clientID,
            self.broker,
            self.port,
            rc,
        )
        print(msg)
        if rc == 0 and self._connected_once and self._topic:
            self._c.subscribe(self._topic, qos=2)
            msg = "[%s] Resubscribed to %s" % (self._clientID, self._topic)
            print(msg)
        self._connected_once = True

    def _on_disconnect(self, client, userdata, rc):
        if rc != 0:
            msg = "[%s] Unexpected disconnect (rc=%s)" % (self._clientID, rc)
            print(msg)
        else:
            msg = "[%s] Disconnected from broker." % (self._clientID)
            print(msg)

    def _on_message(self, client, userdata, msg):
        try:
            self.notifier.notify(msg.topic, msg.payload or b"")
        except Exception:
            msg = "[%s] notifier.notify error" % (self._clientID)
            print(msg)

    # --- api ---

    def start(self):
        msg = "[%s] Connecting to %s:%s ..." % (self._clientID, self.broker, self.port)
        print(msg)
        self._c.connect(self.broker, self.port, keepalive=60)
        self._c.loop_start()

    def MySubscribe(self, topic):
        self._topic = topic
        self._c.subscribe(topic, qos=2)
        msg = "[%s] Subscribed to %s" % (self._clientID, topic)
        print(msg)

    def MyPublish(self, topic, message, retain=False):
        try:
            payload = json.dumps(message, default=str)
        except Exception:
            msg = "[%s] json.dumps failed" % (self._clientID)
            print(msg)
            return None
        info = self._c.publish(topic, payload, qos=2, retain=retain)
        rc = getattr(info, "rc", 0)
        if rc == 0:
            msg = "[%s] Published to %s: %s" % (self._clientID, topic, payload)
            print(msg)
        else:
            msg = "[%s] Publish failed to %s (rc=%s)" % (self._clientID, topic, rc)
            print(msg)
        return info

    def MyUnsubscribe(self):
        if self._topic:
            try:
                self._c.unsubscribe(self._topic)
                msg = "[%s] Unsubscribing from %s" % (self._clientID, self._topic)
                print(msg)
            except Exception:
                msg = "[%s] Unsubscribe error" % (self._clientID)
                print(msg)

    def stop(self):
        self.MyUnsubscribe()
        try:
            self._c.loop_stop()
        except Exception:
            msg = "[%s] loop_stop error" % (self._clientID)
            print(msg)
        try:
            self._c.disconnect()
        except Exception:
            msg = "[%s] disconnect error" % (self._clientID)
            print(msg)
