import logging
from pathlib import Path

from Raspberry_Connector import raspberry
from Raspberry_Connector.sensors.sensor import Sensor
from utils.custom_publisher import CustomPublisher

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'


class DHT11(Sensor):
    def __init__(self, broker_ip, broker_port, parent_topic):
        super().__init__(CONFIG_FILE)
        topic_temperature, topic_humidity = self._build_topics(parent_topic)
        logging.debug('Creating DHT11 publisher for temperature: %s' % topic_temperature)
        self.publisher_temperature = CustomPublisher(client_id=self.device_id, topic=topic_temperature,
                                                     broker=broker_ip, port=broker_port)
        logging.debug('Creating DHT11 publisher for humidity: %s' % topic_humidity)
        self.publisher_humidity = CustomPublisher(client_id=self.device_id, topic=topic_humidity, broker=broker_ip,
                                                  port=broker_port)

    def start(self):
        self.publisher_temperature.start()

    def stop(self):
        self.publisher_temperature.stop()

    def read_value(self):
        self.publisher_temperature.publish('read')
        print('read')
