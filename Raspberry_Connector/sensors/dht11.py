from Raspberry_Connector.sensors.sensor_emulator import *


class DHT11(SensorEmulator):

<<<<<<< HEAD
    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, conf, path=FILE_PATH, seconds=1):
        super().__init__(conf, path, seconds)

        # Update specific info
        self.topic_temperature = self.topic[0]
        self.topic_air_humidity = self.topic[1]
        self.unit_temperature = self.units[0]
        self.unit_air_humidity = self.units[1]

        # No more needed
        del self.topic
        del self.units

        # pd.Series
        self.temperature, self.air_humidity = self.__correct_temp_and_hum_values()
=======
    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=1):
        super().__init__(path, seconds)
        self.temperature, self.air_humidity = self.__correct_temp_and_hum_values()
        self.topic_temperature = 'dht/temperature/data'
        self.topic_air_humidity = 'dht/air_humidity/data'
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)

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
<<<<<<< HEAD
=======


if __name__ == '__main__':
    sensor = DHT11(seconds=3)
    print(sensor.temperature)
    print(sensor.air_humidity)
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)
