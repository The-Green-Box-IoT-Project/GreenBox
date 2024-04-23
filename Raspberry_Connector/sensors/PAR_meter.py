from Raspberry_Connector.sensors.sensor_emulator import *


class PAR_meter(SensorEmulator):
    """
    "Photosynthetically Active Radiation" (Radiazione Fotosinteticamente Attiva)
    """
    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=1):
        super().__init__(path, seconds)
        self.PAR = self.__correct_PAR_values()
        self.topic_PAR = 'PARmeter/PAR/data'

    def __select_PAR(self):
        self.data.rename(columns={'Tot_PAR': 'PAR'}, inplace=True)
        data = self.data[['PAR']]
        PAR = data['PAR']
        return PAR

    def __correct_PAR_values(self):
        PAR = self.__select_PAR()
        PAR = self.correct_values(PAR)
        replace_negatives = lambda x: max(x, 0)
        PAR = PAR.apply(replace_negatives)
        return PAR
