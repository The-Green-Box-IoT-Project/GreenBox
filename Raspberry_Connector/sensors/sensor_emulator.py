import pandas as pd
from datetime import datetime
import warnings
import csv
warnings.filterwarnings("ignore")


class SensorEmulator:

    FILE_PATH = ''

    def __init__(self, conf, path, seconds):

        # To the dataset .csv file
        self.path = path

        # For generate the desired granularity of the data
        self.seconds = seconds

        # sensor's info
        self.name = conf['device_name']
        self.id = conf['sensID']
        self.pin = conf['pin']
        self.field = conf['measurementType']
        self.units = conf['units']
        self.topic = conf['services_details'][0]['topic']

        # sensor measurement
        # meas = {
        #     "topic": self.topic,
        #     "data": {
        #         "field": self.field,
        #         "value": self.value.iloc[count]
        #     }
        # }

        # correctly read data from csv : return pd.Dataframe
        self.data = self.__correct_csv_file()

    @staticmethod
    def __change_time_reference(data):
        num_rows = len(data)
        start_datetime = datetime(2023, 2, 1, 0, 0, 0)
        index = pd.date_range(start=start_datetime, periods=num_rows, freq=f'5T')
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
        data = data.resample(f"{self.seconds}s").mean().interpolate(method='cubic')
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
