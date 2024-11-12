from pathlib import Path
import logging
import time

from utils.custom_publisher import CustomPublisher
from Raspberry_Connector.sensors.sensor import Sensor, SimulateRealTimeReading, hardware_read

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
MOCK_VALUES_FILE = P / 'mock_values.json'


class GrodanSens(Sensor):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(CONFIG_FILE)
        self.topic = self._build_topics(parent_topic)
        self.field = self.measurements[0]['field']
        self.unit = self.measurements[0]['unit']

        logging.debug('Creating Grodan Sensor publisher: %s' % self.topic)
        self.publisher = CustomPublisher(client_id=self.device_id, topic=self.topic,
                                         broker=broker_ip, port=broker_port)

    def start(self):
        self.publisher.start()

    def stop(self):
        self.publisher.stop()

    def read_value(self):
        self.start()
        while True:
            soil_humidity_value = hardware_read(self.device_pin)
            message = {
                self.field: soil_humidity_value,
            }
            self.publisher.publish(message)
            time.sleep(2)


class GrodanSens_sim(GrodanSens):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(
            broker_ip, broker_port,
            parent_topic)

    def read_value(self):
        self.start()
        while True:
            base_value = SimulateRealTimeReading(MOCK_VALUES_FILE, 'soil_humidity').read()
            soil_humidity_value = min(max(base_value, 0), 100)  # Ensures soil_humidity is between 0 and 100
            message = {
                self.field: soil_humidity_value,
            }
            self.publisher.publish(message)
            time.sleep(2)
