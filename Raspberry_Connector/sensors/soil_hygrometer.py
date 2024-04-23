from Raspberry_Connector.sensors.sensor_emulator import *


class GrodanSens(SensorEmulator):

<<<<<<< HEAD
    FILE_PATH = './sensors/data/dataset/GrodanSens.csv'

    def __init__(self, conf, path=FILE_PATH, seconds=1):
        super().__init__(conf, path, seconds)

        # pd.Series
        self.soil_humidity = self.__correct_soil_hum_values()
=======
    FILE_PATH = './data/dataset/GrodanSens.csv'

    def __init__(self, path=FILE_PATH, seconds=1):
        super().__init__(path, seconds)
        self.soil_humidity = self.__correct_soil_hum_values()
        self.topic_soil_humidity = 'grodan/soil_humidity/data'
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)

    def __select_soil_hum(self):
        wc_slab1 = self.data['WC_slab1']
        wc_slab2 = self.data['WC_slab2']
        merged_data = wc_slab1.combine_first(wc_slab2)
        merged_data.rename('soil_humidity', inplace=True)
        return merged_data

    def __correct_soil_hum_values(self):
        data = self.__select_soil_hum()
        data = self.correct_values(data)
        return data
<<<<<<< HEAD
=======


if __name__ == '__main__':
    sensor = GrodanSens(seconds=3)
    print(sensor.soil_humidity)
>>>>>>> 00ef6ca (Created DHT11 and Grodan sensors objects.)
