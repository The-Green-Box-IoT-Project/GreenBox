import json
import paho.mqtt.client as mqtt


class MyMQTT:
    def __init__(self, clientID, broker, port):
        self.broker = broker
        self.port = port
        self.notifier = self.notify
        self.clientID = clientID
        self._topic = ""
        self._isSubscriber = False
        # create an instance of paho.mqtt.client
        self._paho_mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, clientID)
        # register the callback
        self._paho_mqtt.on_connect = self.myOnConnect
        self._paho_mqtt.on_message = self.myOnMessageReceived

    @staticmethod
    def notify(topic, payload):
        print(f"Received message on topic '{topic}': {payload}")

    def myOnConnect(self, client, userdata, flags, reason_code, properties=None):
        if hasattr(flags, 'session_present'):
            session_present = flags.session_present
        else:
            session_present = flags.get("session present", False)

        if session_present:
            print("Session present.")

        if reason_code == 0:
            print("Connected to %s with success." % self.broker)
        else:
            print("Connection failed with reason code: %d" % reason_code)

    def myOnMessageReceived(self, client, userdata, message):
        # A new message is received
        self.notifier(message.topic, message.payload)

    def myPublish(self, topic, msg):
        # publish a message with a certain topic
        print(f"Publishing message on topic '{topic}': {msg}")
        self._paho_mqtt.publish(topic, json.dumps(msg), 2)

    def mySubscribe(self, topic):
        # subscribe for a topic
        self._paho_mqtt.subscribe(topic, 2)
        # just to remember that it works also as a subscriber
        self._isSubscriber = True
        self._topic = topic
        print("subscribed to %s" % topic)

    def check_publish_status(self, mid):
        self._paho_mqtt.loop()

    def start(self):
        # manage connection to broker
        self._paho_mqtt.connect(self.broker, self.port)
        self._paho_mqtt.loop_start()

    def unsubscribe(self):
        if self._isSubscriber:
            # remember to unsubscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic)

    def stop(self):
        if self._isSubscriber:
            # remember to unsubscribe if it is working also as subscriber
            self._paho_mqtt.unsubscribe(self._topic)

        self._paho_mqtt.loop_stop()
        self._paho_mqtt.disconnect()
