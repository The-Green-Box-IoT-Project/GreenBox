from pathlib import Path
import logging
import time

from utils.custom_publisher import CustomPublisher
from Raspberry_Connector.sensors.sensor import Sensor, SimulateRealTimeReading, hardware_read

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
MOCK_VALUES_FILE = P / 'mock_values.json'


class PAR_meter(Sensor):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(CONFIG_FILE)
        self.topic = self._build_topics(parent_topic)
        self.field = self.measurements[0]['field']
        self.unit = self.measurements[0]['unit']

        logging.debug('Creating PAR meter publisher: %s' % self.topic)
        self.publisher = CustomPublisher(client_id=self.device_id, topic=self.topic,
                                         broker=broker_ip, port=broker_port)

    def start(self):
        self.publisher.start()

    def stop(self):
        self.publisher.stop()

    def read_value(self):
        self.start()
        while True:
            light_value = hardware_read(self.device_pin)
            message = {
                self.field: light_value,
            }
            self.publisher.publish(message)
            time.sleep(2)


class PAR_meter_sim(PAR_meter):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(
            broker_ip, broker_port,
            parent_topic)

    def read_value(self):
        self.start()
        while True:
            base_value = SimulateRealTimeReading(MOCK_VALUES_FILE, 'light').read()
            light_value = max(base_value, 0)  # Ensures light_value is bigger than 0
            message = {
                self.field: light_value,
            }
            self.publisher.publish(message)
            time.sleep(2)
