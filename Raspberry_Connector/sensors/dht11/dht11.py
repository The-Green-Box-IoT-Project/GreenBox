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

    def read_value(self):
        print('read')


if __name__ == '__main__':
    device_id, device_name = raspberry.retrieve_device()
    catalog_ip, catalog_port = raspberry.retrieve_catalog()
    broker_ip, broker_port = raspberry.retrieve_broker(catalog_ip, catalog_port)
    parent_topic = raspberry.build_parent_topic(device_id)
    sensor_dht11 = DHT11(broker_ip=broker_ip, broker_port=broker_port, parent_topic=parent_topic)
