import logging

import paho.mqtt.client as mqtt


class CustomPublisher:
    def __init__(self, client_id, topic, broker='mqtt.eclipseprojects.io'):
        self.client_id = client_id
        self.topic = topic
        self.broker = broker

        # client initialization
        self._mqtt = mqtt.Client(client_id=client_id, clean_session=True)
        # registering callbacks
        self._mqtt.on_connect = self.on_connect

    def start(self):
        self._mqtt.connect(self.broker, 1883)
        self._mqtt.loop_start()

    def stop(self):
        self._mqtt.loop_stop()
        self._mqtt.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        logging.debug('Client "%s" connected to broker "%s" with result code: %d' % (client, self.broker, rc))

    def publish(self, message, qos=0):
        logging.debug('Client "%s" published message on topic "%s": "%s"' % (self.client_id, self.topic, message))
        self._mqtt.publish(self.topic, message, qos)
