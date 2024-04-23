from Raspberry_Connector.sensors.sensor_emulator import *


class PH_meter(SensorEmulator):

    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=1):
        super().__init__(path, seconds)
        self.pH = self.__correct_pH_values()
        self.topic_pH = 'pHmeter/pH/data'

    def __select_pH(self):
        self.data.rename(columns={'pH_drain_PC': 'pH'}, inplace=True)
        data = self.data[['pH']]
        pH = data['pH']
        return pH

    def __correct_pH_values(self):
        pH = self.__select_pH()
        pH = self.correct_values(pH)
        return pH
