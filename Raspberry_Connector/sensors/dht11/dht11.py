from pathlib import Path
import logging
import time

from utils.custom_publisher import CustomPublisher
from Raspberry_Connector.sensors.sensor import Sensor, SimulateRealTimeReading, hardware_read

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
MOCK_VALUES_FILE = P / 'mock_values.json'


class DHT11(Sensor):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(CONFIG_FILE)

        self.topic = self._build_topics(parent_topic)
        self.field_temperature = self.measurements[0]['field']
        self.field_humidity = self.measurements[1]['field']
        self.unit_temperature = self.measurements[0]['unit']
        self.unit_humidity = self.measurements[1]['unit']

        logging.debug('Creating DHT11 publisher: %s' % self.topic)
        self.publisher = CustomPublisher(client_id=self.device_id, topic=self.topic,
                                         broker=broker_ip, port=broker_port)

    def start(self):
        self.publisher.start()

    def stop(self):
        self.publisher.stop()

    def read_value(self):
        self.start()
        while True:
            temperature_value = hardware_read(self.device_pin)
            humidity_value = hardware_read(self.device_pin)
            message = {
                self.field_temperature: temperature_value,
                self.field_humidity: humidity_value,
            }
            self.publisher.publish(message)
            time.sleep(2)


class DHT11sim(DHT11):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(
            broker_ip, broker_port,
            parent_topic)

    def read_value(self):
        self.start()
        while True:
            temperature_value = SimulateRealTimeReading(MOCK_VALUES_FILE, 'temperature').read()
            base_value = SimulateRealTimeReading(MOCK_VALUES_FILE, 'humidity').read()
            humidity_value = min(max(base_value, 0), 100)  # Ensures humidity_value is between 0 and 100
            message = {
                self.field_temperature: temperature_value,
                self.field_humidity: humidity_value
            }
            self.publisher.publish(message)
            time.sleep(2)
