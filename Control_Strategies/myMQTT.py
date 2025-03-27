import paho.mqtt.client as mqtt
import json
class MyMQTT:
    def __init__(self, broker, port, clientID, notifier=None):
        self.broker = broker
        self.port = port
        self.clientID = clientID
        self.notifier = notifier
        
        
        self._client = mqtt.Client(client_id=clientID, protocol=mqtt.MQTTv311)
        
        
        self._client.on_connect = self.on_connect
        self._client.on_disconnect = self.on_disconnect
        self._client.on_publish = self.on_publish
        self._client.on_message = self.on_message

    def on_connect(self, client, userdata, flags, rc, properties=None):
        print("Connected to broker {}:{} with result code: {}".format(self.broker, self.port, rc))
        
        
    # Callback on_disconnect 
    def on_disconnect(self, client, userdata, rc, properties=None):
        print("Disconnected with result code: {}".format(rc))
        
    # Callback on_publish
    def on_publish(self, client, userdata, mid):
        print("Message published with mid: {}".format(mid))
        
    # Callback on_message
    def on_message(self, client, userdata, message):
        print("Message received on topic: {}".format(message.topic))
        print("Payload: {}".format(message.payload.decode()))

    def connect(self):
        self._client.connect(self.broker, self.port, keepalive=60)
        self._client.loop_start()

    def disconnect(self):
        self._client.loop_stop()
        self._client.disconnect()

    def publish(self, topic, payload):
        # Serialize the payload to a JSON string
        if isinstance(payload, dict):
            payload = json.dumps(payload)
        self._client.publish(topic, payload)