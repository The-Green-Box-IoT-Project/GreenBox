from Raspberry_Connector.sensors.sensor_emulator import *


class DHT11(SensorEmulator):

    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, conf, path=FILE_PATH, seconds=3):
        super().__init__(conf, path, seconds)

        # Update specific info
        self.topic_temperature = self.topic[0]
        self.topic_air_humidity = self.topic[1]
        self.unit_temperature = self.units[0]
        self.unit_air_humidity = self.units[1]
        self.field_temp = self.field[0]
        self.field_air_humidity = self.field[1]

        # pd.Series
        self.temperature, self.air_humidity = self.__correct_temp_and_hum_values()

    def __select_temp_and_hum(self):
        self.data.rename(columns={'Rhair': 'air_humidity', 'Tair': 'temperature'}, inplace=True)
        data = self.data[['air_humidity', 'temperature']]
        temperature, humidity = data['temperature'], data['air_humidity']
        return temperature, humidity

    def __correct_temp_and_hum_values(self):
        temperature, humidity = self.__select_temp_and_hum()
        temperature = self.correct_values(temperature)
        humidity = self.correct_values(humidity)
        return temperature, humidity


class TempSensor(DHT11):

    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, conf, path=FILE_PATH, seconds=3):
        super().__init__(conf, path, seconds)

        self.value = self.temperature
        self.topic = self.topic_temperature
        self.field = self.field_temp
        self.units = self.unit_temperature


class AirHumSensor(DHT11):

    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, conf, path=FILE_PATH, seconds=3):
        super().__init__(conf, path, seconds)

        self.value = self.air_humidity
        self.topic = self.topic_air_humidity
        self.field = self.field_air_humidity
        self.units = self.unit_air_humidity
