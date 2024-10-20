from Raspberry_Connector.sensors.sensor_emulator import *


class PAR_meter(SensorEmulator):
    """
    "Photosynthetically Active Radiation" (Radiazione Fotosinteticamente Attiva)
    """
    FILE_PATH = './sensors/data/dataset/GreenhouseClimate.csv'

    def __init__(self, conf, path=FILE_PATH, seconds=10):
        super().__init__(conf, path, seconds)

        # pd.Series
        self.value = self.__correct_PAR_values()

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
