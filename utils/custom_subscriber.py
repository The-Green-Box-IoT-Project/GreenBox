import logging

import paho.mqtt.client as mqtt


class CustomSubscriber:
    def __init__(self, client_id, topics, broker):
        self.client_id = client_id
        self.topics = topics
        self.broker = broker

        # client initialization
        self._mqtt = mqtt.Client(client_id=client_id, clean_session=False)
        # registering callbacks
        self._mqtt.on_connect = self.on_connect

    def start(self, qos=0):
        self._mqtt.connect(self.broker, port=1883)
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
