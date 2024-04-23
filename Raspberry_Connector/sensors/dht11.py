from Raspberry_Connector.sensors.sensor_emulator import *


class DHT11(SensorEmulator):

    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=1):
        super().__init__(path, seconds)
        self.temperature, self.air_humidity = self.__correct_temp_and_hum_values()
        self.topic_temperature = 'dht/temperature/data'
        self.topic_air_humidity = 'dht/air_humidity/data'

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


if __name__ == '__main__':
    sensor = DHT11(seconds=3)
    print(sensor.temperature)
    print(sensor.air_humidity)
