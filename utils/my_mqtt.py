import logging
import json
import paho.mqtt.client as mqtt


class MyMQTT:
    def __init__(self, clientID, topic, broker='mqtt.eclipseprojects.io', port=1883):

        self.clientID = clientID
        self.topic = topic
        self.broker = broker
        self.port = port

        self.notifier = self.notify
        self._isSubscriber = False

        # create an instance of paho.mqtt.client
        self._paho_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, clientID)

        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    @staticmethod
    def notify(topic, payload):
        logging.debug(f"Received message on topic '{topic}': {payload}")

    def myOnConnect(self, client, userdata, flags, reason_code, properties=None):
        if hasattr(flags, 'session_present'):
            session_present = flags.session_present
        else:
            session_present = flags.get("session present", False)

        if session_present:
            logging.debug("Session present.")

        if reason_code == 0:
            logging.debug("Connected to %s with success." % self.broker)
        else:
            logging.debug("Connection failed with reason code: %d" % reason_code)

    def myOnMessageReceived(self, client, userdata, message):
        # A new message is received
        self.notifier(message.topic, message.payload)

    def myPublish(self, topic, msg):
        # publish a message with a certain topic
        logging.debug(f"Publishing message on topic '{topic}': {msg}")
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)

    def mySubscribe(self, topic):
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        self._topic = topic
        logging.debug("subscribed to %s" % topic)

    def unsubscribe(self):
        if self._isSubscriber:
            # remember to unsubscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic)

    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def stop(self):
        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
