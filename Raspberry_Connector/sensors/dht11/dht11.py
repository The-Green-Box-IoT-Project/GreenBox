from pathlib import Path
import logging
import time

from utils.custom_publisher import CustomPublisher
from Raspberry_Connector.sensors.sensor import Sensor, hardware_read
from Raspberry_Connector.sensors.generate_mock_time_series import SensorSimulator, MockTimeSeriesWrapper, Today, \
    SimulateRealTimeReading

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
        # self.publisher_temperature.start()
        self.publisher.start()

    def stop(self):
        # self.publisher_temperature.stop()
        self.publisher.stop()

    def _get_last_measurement(self):
        message = {
            self.field_temperature: hardware_read(self.device_pin),
            self.field_humidity: hardware_read(self.device_pin),
        }
        return message

    def read_value(self):
        self.start()
        while True:
            message = self._get_last_measurement()
            self.publisher.publish(message)
            time.sleep(2)


class DHT11sim(DHT11):
    def __init__(self,
                 broker_ip, broker_port,
                 parent_topic):
        super().__init__(
            broker_ip, broker_port,
            parent_topic)

        self.sensor_simulator = SensorSimulator(MOCK_VALUES_FILE)
        self.temperature_values = self.generate_mock_value('temperature')
        self.humidity_values = self.generate_mock_value('humidity')

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

    def _get_last_measurement(self):
        temperature_value = self.temperature_values.read_last_measurement()
        humidity_value = self.humidity_values.read_last_measurement()
        message = {
            self.field_temperature: temperature_value,
            self.field_humidity: humidity_value
        }
        return message

    def read_value(self):
        self.start()
        while True:
            message = self._get_last_measurement()
            self.publisher.publish(message)
            time.sleep(2)
