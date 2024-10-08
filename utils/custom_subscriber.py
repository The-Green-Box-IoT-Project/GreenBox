import logging

import paho.mqtt.client as mqtt


class CustomSubscriber:
    def __init__(self, client_id, topics, broker):
        self.client_id = client_id
        self.topics = topics
        self.broker = broker

        # client initialization
        self._mqtt = mqtt.Client(client_id=client_id, clean_session=True)
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
        logging.debug('Client "%s" connected to broker "%s" with result code: %d' % (client, self.broker, rc))

    def on_message(self, client, userdata, msg):
        print('Client "%s" received message on topic "TODO": %s' % msg.payload)
