import pandas as pd
from datetime import datetime
import warnings
import logging
import csv
warnings.filterwarnings("ignore")


class SensorSimulator:

    FILE_PATH = ''

    def __init__(self, path, seconds):

        # To the dataset .csv file
        self.path = path

        # For generate the desired granularity of the data
        self.seconds = seconds

        # correctly read data from csv : return pd.Dataframe
        self.data = self.__correct_csv_file()

    @staticmethod
    def __change_time_reference(data):
        num_rows = len(data)
        start_datetime = datetime(2024, 1, 1, 0, 0, 0)
        index = pd.date_range(start=start_datetime, periods=num_rows, freq=f'6T')
        data.index = index
        data.drop(columns=['%time'], axis=1, inplace=True)
        return data

    @staticmethod
    def check_NaN_values(df):
        nan_count = df.isnull().sum().sum()  # Number of NaN values for each column
        nans = nan_count > 0  # Returns True if there are any NaN values, False otherwise
        return nans

    @staticmethod
    def fill_dataset(df):
        df = df.interpolate(method='linear')
        df = df.fillna(method='bfill')
        df = df.fillna(method='ffill')
        return df

    @staticmethod
    def __correct_non_numeric_values(df):
        mask = df.apply(lambda s: pd.to_numeric(s, errors='coerce').notnull().all())
        if not mask.any():
            # Convert column values to numbers
            for column in df.columns:
                if df[column].dtype == 'object':
                    df[column] = pd.to_numeric(df[column],
                                               errors='coerce')  # errors='coerce' will convert non-numeric values to NaN
        return df

    def __correct_str_to_float(self):
        new_data = []
        with open(self.FILE_PATH, 'r') as file:
            reader = csv.reader(file)
            for i, row in enumerate(reader):
                if i == 0:
                    new_data.append(row)
                else:
                    converted_row = [float(cell) for cell in row]
                    new_data.append(converted_row)
        columns = new_data[0]
        data = new_data[1:]
        dataframe = pd.DataFrame(data, columns=columns)
        return dataframe

    def __correct_csv_file(self):
        dataframe = self.__correct_str_to_float()
        dataframe = self.__correct_non_numeric_values(dataframe)
        return dataframe

    def __resample_dataframe(self, data):
        data = data.resample(f"{self.seconds}s").mean().interpolate(method='linear')
        return data

    def __change_granularity(self, data):
        data = self.__resample_dataframe(data)
        if self.check_NaN_values(data):
            data = self.fill_dataset(data)
        data = data.round(2)
        return data

    def correct_values(self, data):
        data = self.fill_dataset(data)
        data = self.__change_time_reference(data)
        data = self.__change_granularity(data)
        return data

    @staticmethod
    def mirror_data(series, seconds):

        # Seleziona i dati dal 1 gennaio al 1 luglio compreso
        df = series.loc['2024-01-01':'2024-07-01']

        # Copia i dati da gennaio a luglio
        df_copy = df.copy()

        # Inverti l'ordine dei dati copiati
        df_copy = df_copy[::-1]

        # Genera nuove timestamp della stessa lunghezza del DataFrame copiato
        last_timestamp = pd.to_datetime(df.index[-1])
        new_timestamps = pd.date_range(start=last_timestamp + pd.Timedelta(seconds=seconds),
                                       periods=len(df_copy), freq=f'{seconds}S')

        # Imposta le nuove timestamp invertite sul DataFrame copiato
        df_copy.index = new_timestamps

        # Unisci il DataFrame originale con quello invertito
        df_final = pd.concat([df, df_copy])

        return df_final

    def read_current_value(df):

        # Get the current timestamp
        current_time = pd.Timestamp(datetime.now())

        # Calculates the absolute difference between the current timestamp and the index of the DataFrame
        time_differences = abs(df.index - current_time)

        # Find the index with the smallest time difference
        closest_index = time_differences.argmin()

        # Get the value corresponding to the nearest timestamp
        closest_value = df.iloc[closest_index]

        # Print or use the value as desired
        logging.debug(
            f"Il valore di umidità dell'aria più vicino a {current_time} è: {closest_value} (corrispondente a {df.index[closest_index]})")

        return closest_value


class PH_meter_sim(SensorSimulator):

    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=20):
        super().__init__(path, seconds)

        # pd.Series
        self.value = self._get_data()

    def _select_pH(self):
        self.data.rename(columns={'pH_drain_PC': 'pH'}, inplace=True)
        data = self.data[['pH']]
        pH = data['pH']
        return pH

    def _correct_pH_values(self):
        pH = self._select_pH()
        pH = self.correct_values(pH)
        return pH

    def _get_data(self):
        data = self._correct_pH_values()
        more_data = self.mirror_data(data, self.seconds)
        return more_data


class PAR_meter_sim(SensorSimulator):
    """
    "Photosynthetically Active Radiation" (Radiazione Fotosinteticamente Attiva)
    """
    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=10):
        super().__init__(path, seconds)

        # pd.Series
        self.value = self._get_data()

    def _select_PAR(self):
        self.data.rename(columns={'Tot_PAR': 'PAR'}, inplace=True)
        data = self.data[['PAR']]
        PAR = data['PAR']
        return PAR

    def _correct_PAR_values(self):
        PAR = self._select_PAR()
        PAR = self.correct_values(PAR)
        replace_negatives = lambda x: max(x, 0)
        PAR = PAR.apply(replace_negatives)
        return PAR

    def _get_data(self):
        data = self._correct_PAR_values()
        more_data = self.mirror_data(data, self.seconds)
        return more_data


class GrodanSens_sim(SensorSimulator):

    FILE_PATH = './data/dataset/GrodanSens.csv'

    def __init__(self, path=FILE_PATH, seconds=15):
        super().__init__(path, seconds)

        # pd.Series
        self.value = self._get_data()

    def _select_soil_hum(self):
        wc_slab1 = self.data['WC_slab1']
        wc_slab2 = self.data['WC_slab2']
        merged_data = wc_slab1.combine_first(wc_slab2)
        merged_data.rename('soil_humidity', inplace=True)
        return merged_data

    def _correct_soil_hum_values(self):
        data = self._select_soil_hum()
        data = self.correct_values(data)
        return data

    def _get_data(self):
        data = self._correct_soil_hum_values()
        more_data = self.mirror_data(data, self.seconds)
        return more_data


class DHT11_sim(SensorSimulator):

    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=3):
        super().__init__(path, seconds)

        # pd.Series
        self.temperature, self.air_humidity = self._get_data()

    def _select_temp_and_hum(self):
        self.data.rename(columns={'Rhair': 'air_humidity', 'Tair': 'temperature'}, inplace=True)
        data = self.data[['air_humidity', 'temperature']]
        temperature, humidity = data['temperature'], data['air_humidity']
        return temperature, humidity

    def _correct_temp_and_hum_values(self):
        temperature, humidity = self._select_temp_and_hum()
        temperature = self.correct_values(temperature)
        humidity = self.correct_values(humidity)
        return temperature, humidity

    def _get_data(self):
        temperature, air_humidity = self._correct_temp_and_hum_values()
        more_temperature_data = self.mirror_data(temperature, self.seconds)
        more_humidity_data = self.mirror_data(air_humidity, self.seconds)
        return more_temperature_data, more_humidity_data


class TempSensor_sim(DHT11_sim):

    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=3):
        super().__init__(path, seconds)

        self.value = self.temperature


class AirHumSensor_sim(DHT11_sim):

    FILE_PATH = './data/dataset/GreenhouseClimate.csv'

    def __init__(self, path=FILE_PATH, seconds=3):
        super().__init__(path, seconds)

        self.value = self.air_humidity

if __name__ == '__main__':
    df = AirHumSensor_sim().value

    # Passo 1: Ottieni il timestamp attuale
    current_time = pd.Timestamp(datetime.now())

    # Passo 2: Calcola la differenza assoluta tra il timestamp attuale e l'indice del DataFrame
    time_differences = abs(df.index - current_time)

    # Passo 3: Trova l'indice con la differenza temporale minima
    closest_index = time_differences.argmin()

    # Passo 4: Prendi il valore corrispondente al timestamp più vicino
    closest_value = df.iloc[closest_index]

    # Passo 5: Stampa o utilizza il valore come desiderato
    print(f"Il valore di umidità dell'aria più vicino a {current_time} è: {closest_value} (corrispondente a {df.index[closest_index]})")