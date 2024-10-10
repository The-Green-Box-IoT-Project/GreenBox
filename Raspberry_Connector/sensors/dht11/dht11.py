import logging

import paho.mqtt.client as mqtt

from Raspberry_Connector.sensors.sensor import Sensor


class DHT11(Sensor):
    def __init__(self, parent_topic, server_ip, port):
        super().__init__()
        self.topic = parent_topic + '/' + self.device_id
        self.broker_ip = server_ip
        self.port = port
        self.connected = False

        # client initialization
        self._mqtt = mqtt.Client(client_id=self.device_id, clean_session=False)
        # registering callbacks
        self._mqtt.on_connect = self.on_connect

    def start(self):
        self._mqtt.connect(self.broker_ip, self.port)
        self._mqtt.loop_start()

    def stop(self):
        self._mqtt.loop_stop()
        self._mqtt.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        self.connected = True
        logging.debug('Connected to the broker with result code: %d' % rc)

    def publish(self, message, qos=2):
        logging.debug('Client "%s" published message on topic "%s": "%s"' % (self.client_id, self.topic, message))
        self._mqtt.publish(self.topic, message, qos)


if __name__ == '__main__':
    # TODO: retrieve user data to build full topic
    pass
