import logging
from time import sleep

import paho.mqtt.client as mqtt


class CustomSubscriber:
    def __init__(self, client_id, topics, broker='mqtt.eclipseprojects.io', port=1883):
        self.client_id = client_id
        self.topics = topics
        self.broker = broker
        self.port = port

        # client initialization
        self._mqtt = mqtt.Client(mqtt.CallbackAPIVersion.VERSION1, client_id=client_id, clean_session=False)
        # registering callbacks
        self._mqtt.on_connect = self.on_connect
        self._mqtt.on_message = self.on_message

    def start(self, qos=2):
        self._mqtt.connect(self.broker, port=self.port)
        self._mqtt.loop_start()
        self._mqtt.subscribe(self.topics, qos=qos)

    def stop(self):
        self._mqtt.unsubscribe(self.topics)
        self._mqtt.loop_stop()
        self._mqtt.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        logging.debug('Connected to the broker with result code: %d' % rc)

    def on_message(self, client, userdata, msg):
        logging.debug('Received message: %s' % msg.payload)


if __name__ == '__main__':
    sub = CustomSubscriber(client_id='teeest',
                           topics='/01f20b9e-6df4-43df-9fd6-c1376bb2ba41/greenhouse1/rb01/dht11/temperature')
    sub.start()
    while True:
        sleep(1)
