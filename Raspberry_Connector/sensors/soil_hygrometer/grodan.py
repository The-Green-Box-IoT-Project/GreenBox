from pathlib import Path
import logging
import numpy as np

from utils.custom_publisher import CustomPublisher
from Raspberry_Connector.sensors.sensor import Sensor, hardware_read
from Raspberry_Connector.sensors.generate_mock_time_series import SensorSimulator, MockTimeSeriesWrapper, SimulateRealTimeReading, Today

P = Path(__file__).parent.absolute()
CONFIG_FILE = P / 'config.json'
MOCK_VALUES_FILE = P / 'mock_values.json'


class GrodanSens(Sensor):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(CONFIG_FILE)
        self.topic = next(self._build_topics(parent_topic))
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
        message = {
            self.field: hardware_read(self.device_pin),
        }
        return message


class GrodanSens_sim(GrodanSens):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(
            broker_ip, broker_port,
            parent_topic)

        self.sensor_simulator = SensorSimulator(MOCK_VALUES_FILE)
        self.pH_values = self.generate_mock_value('soil_humidity')

    def custom_time_series(self, measurement_name):
        mock_values = self.sensor_simulator.measures[measurement_name]
        wrapper = MockTimeSeriesWrapper(mock_values, Today().start, Today().end)

        trend = wrapper.generate_trend()
        daily_seasonality = wrapper.generate_daily_seasonality()
        yearly_seasonality = wrapper.generate_yearly_seasonality()
        noise = wrapper.generate_noise()

        time_series_shape = trend + daily_seasonality + yearly_seasonality + noise
        time_series_index = wrapper.ts_index

        return time_series_shape, time_series_index

    def generate_mock_value(self, measurement_name):
        time_series_shape, time_series_index = self.custom_time_series(measurement_name)
        return SimulateRealTimeReading(time_series_shape, time_series_index, measurement_name)

    def read_value(self):
        value = self.pH_values.read_last_measurement()
        message = {
            self.field: round(value, 1)
        }
        return message
